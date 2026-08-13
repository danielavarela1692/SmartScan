import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, ValidationError

from ..config import settings
from ..ingestion.base import RawDocument
from ..matching import MatchStore, ProviderItem, get_items_catalog_client
from ..matching.store import normalize_text
from ..pipeline import ExtractionResult, extract_raw, resolve_concepts, to_service_expense

TEMPLATE_PATH = Path(__file__).parent / "review.html"
STATUS_TEMPLATE_PATH = Path(__file__).parent / "status.html"


def _ranked_candidates(detail: str, candidates: list[ProviderItem]) -> list[dict]:
    """Ordena las opciones de mayor a menor parecido de texto, para sugerir
    primero la mas probable. Esto es solo para ayudar a elegir mas rapido en
    la revision humana - el auto-match sigue siendo por coincidencia exacta."""
    detail_norm = normalize_text(detail)
    scored = [
        (
            round(SequenceMatcher(None, detail_norm, normalize_text(c.description)).ratio() * 100),
            c,
        )
        for c in candidates
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [{"concept_id": c.concept_id, "description": c.description, "score": score} for score, c in scored]


class HeaderOverrideStore:
    """Correcciones manuales a los datos de encabezado (CUIT, proveedor,
    numero, total) cuando la extraccion automatica se equivoca o no
    encuentra algo. Mismo patron que MatchStore, pero por documento."""

    def __init__(self, path: Path):
        self.path = path
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, filename: str) -> dict:
        return self._data.get(filename, {})

    def set(self, filename: str, fields: dict) -> None:
        current = self._data.get(filename, {})
        current.update(fields)
        self._data[filename] = current
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_app(inbox_dir: Path, outbox_dir: Path) -> FastAPI:
    app = FastAPI(title="Panel de revision - Fase 2")
    outbox_dir.mkdir(parents=True, exist_ok=True)
    catalog = get_items_catalog_client(settings).get_items()
    store = MatchStore(Path(settings.match_store_path))
    header_store = HeaderOverrideStore(Path(settings.header_overrides_path))

    def _load_document(pdf_path: Path):
        content = pdf_path.read_bytes()
        document = RawDocument(filename=pdf_path.name, content=content, origin=f"manual:{pdf_path}")
        raw = extract_raw(document)

        overrides = header_store.get(pdf_path.name)
        if overrides.get("cuit"):
            raw.cuit = overrides["cuit"]
        if overrides.get("name"):
            raw.name = overrides["name"]
        if overrides.get("number"):
            raw.number = overrides["number"]
        if overrides.get("total") is not None:
            raw.total = overrides["total"]

        needs_header = not raw.cuit or not raw.number
        if needs_header:
            result = ExtractionResult(document=document, raw=raw, errors=[])
            return result, [], True

        try:
            service_expense = to_service_expense(raw)
        except ValidationError as exc:
            errors = [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()]
            return ExtractionResult(document=document, raw=raw, errors=errors), [], False

        result = ExtractionResult(document=document, raw=raw, service_expense=service_expense)
        outcomes = resolve_concepts(result, catalog, store)
        return result, outcomes, False

    @app.get("/", response_class=HTMLResponse)
    def status_page():
        return STATUS_TEMPLATE_PATH.read_text(encoding="utf-8")

    @app.get("/panel", response_class=HTMLResponse)
    def index():
        return TEMPLATE_PATH.read_text(encoding="utf-8")

    @app.get("/api/stats")
    def stats():
        pending = sum(
            1
            for pdf_path in inbox_dir.glob("*.pdf")
            if not (outbox_dir / f"{pdf_path.name}.json").exists()
        )
        approved = sum(1 for _ in outbox_dir.glob("*.json"))
        return {"pending": pending, "approved": approved}

    @app.get("/api/documents")
    def list_documents():
        documents = []
        for pdf_path in sorted(inbox_dir.glob("*.pdf")):
            if (outbox_dir / f"{pdf_path.name}.json").exists():
                continue  # ya aprobada en una corrida anterior

            result, outcomes, needs_header = _load_document(pdf_path)
            raw = result.raw

            if result.errors and not needs_header:
                documents.append({"filename": pdf_path.name, "errors": result.errors, "needs_header": False})
                continue

            items = []
            if not needs_header:
                items = [
                    {
                        "detail": outcome.item.detail,
                        "quantity": outcome.item.quantity,
                        "unit_price": outcome.item.unit_price,
                        "total": outcome.item.total,
                        "concept_id": outcome.concept_id,
                        "resolved": outcome.resolved,
                        "candidates": (
                            [] if outcome.resolved else _ranked_candidates(outcome.item.detail, outcome.candidates)
                        ),
                    }
                    for outcome in outcomes
                ]

            documents.append(
                {
                    "filename": pdf_path.name,
                    "errors": [],
                    "needs_header": needs_header,
                    "cuit": raw.cuit or "",
                    "name": raw.name or "",
                    "number": raw.number or "",
                    "total": raw.total,
                    "items": items,
                    "all_resolved": (not needs_header) and (all(item["resolved"] for item in items) if items else True),
                }
            )
        return documents

    @app.get("/api/pdf/{filename}")
    def get_pdf(filename: str):
        pdf_path = (inbox_dir / filename).resolve()
        if inbox_dir.resolve() not in pdf_path.parents or not pdf_path.exists():
            raise HTTPException(status_code=404, detail="No encontrado")
        return FileResponse(pdf_path, media_type="application/pdf")

    class HeaderOverrideInput(BaseModel):
        cuit: Optional[str] = None
        name: Optional[str] = None
        number: Optional[str] = None
        total: Optional[float] = None

    @app.post("/api/documents/{filename}/header")
    def save_header_override(filename: str, body: HeaderOverrideInput):
        fields = {k: v for k, v in body.model_dump().items() if v not in (None, "")}
        header_store.set(filename, fields)
        return {"ok": True}

    class ResolveInput(BaseModel):
        cuit: str
        detail: str
        concept_id: str

    @app.post("/api/resolve")
    def resolve_line(body: ResolveInput):
        store.set(body.cuit, body.detail, body.concept_id)
        return {"ok": True}

    @app.post("/api/approve/{filename}")
    def approve(filename: str):
        pdf_path = inbox_dir / filename
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="No encontrado")

        result, outcomes, needs_header = _load_document(pdf_path)
        if needs_header:
            raise HTTPException(status_code=400, detail="Faltan completar datos del encabezado (CUIT y/o numero)")
        if result.errors:
            raise HTTPException(status_code=400, detail="; ".join(result.errors))

        pending = [o.item.detail for o in outcomes if not o.resolved]
        if pending:
            raise HTTPException(status_code=400, detail=f"Faltan resolver: {', '.join(pending)}")

        out_path = outbox_dir / f"{filename}.json"
        out_path.write_text(
            json.dumps(result.service_expense.model_dump(by_alias=True, mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"ok": True, "path": str(out_path)}

    return app

import json
from difflib import SequenceMatcher
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from ..config import settings
from ..ingestion.base import RawDocument
from ..matching import MatchStore, ProviderItem, get_items_catalog_client
from ..matching.store import normalize_text
from ..pipeline import process_document, resolve_concepts


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

TEMPLATE_PATH = Path(__file__).parent / "review.html"


def create_app(inbox_dir: Path, outbox_dir: Path) -> FastAPI:
    app = FastAPI(title="Panel de revision - Fase 2")
    outbox_dir.mkdir(parents=True, exist_ok=True)
    catalog = get_items_catalog_client(settings).get_items()
    store = MatchStore(Path(settings.match_store_path))

    def _load_document(pdf_path: Path):
        content = pdf_path.read_bytes()
        document = RawDocument(filename=pdf_path.name, content=content, origin=f"manual:{pdf_path}")
        result = process_document(document)
        outcomes = resolve_concepts(result, catalog, store)
        return result, outcomes

    @app.get("/", response_class=HTMLResponse)
    def index():
        return TEMPLATE_PATH.read_text(encoding="utf-8")

    @app.get("/api/documents")
    def list_documents():
        documents = []
        for pdf_path in sorted(inbox_dir.glob("*.pdf")):
            if (outbox_dir / f"{pdf_path.name}.json").exists():
                continue  # ya aprobada en una corrida anterior

            result, outcomes = _load_document(pdf_path)
            if result.errors:
                documents.append({"filename": pdf_path.name, "errors": result.errors})
                continue

            expense = result.service_expense
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
                    "cuit": expense.cuit,
                    "name": expense.name,
                    "number": expense.number,
                    "total": expense.total,
                    "items": items,
                    "all_resolved": all(item["resolved"] for item in items) if items else True,
                }
            )
        return documents

    @app.get("/api/pdf/{filename}")
    def get_pdf(filename: str):
        pdf_path = (inbox_dir / filename).resolve()
        if inbox_dir.resolve() not in pdf_path.parents or not pdf_path.exists():
            raise HTTPException(status_code=404, detail="No encontrado")
        return FileResponse(pdf_path, media_type="application/pdf")

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

        result, outcomes = _load_document(pdf_path)
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

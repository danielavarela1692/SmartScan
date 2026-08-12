import json
from pathlib import Path


def normalize_text(text: str) -> str:
    return " ".join(text.strip().upper().split())


class MatchStore:
    """Recuerda, por proveedor, a que item de compra corresponde cada texto de
    linea que una persona ya resolvio a mano. Guardado como JSON plano: no hace
    falta una base de datos para el volumen de esta etapa."""

    def __init__(self, path: Path):
        self.path = path
        self._data: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _key(self, cuit: str, detail: str) -> str:
        return f"{cuit}|{normalize_text(detail)}"

    def get(self, cuit: str, detail: str) -> str | None:
        return self._data.get(self._key(cuit, detail))

    def set(self, cuit: str, detail: str, concept_id: str) -> None:
        self._data[self._key(cuit, detail)] = concept_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

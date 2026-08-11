from pathlib import Path
from typing import Iterator

from .base import RawDocument, Source


class ManualSource(Source):
    def __init__(self, folder: Path, processed_marker: str = ".processed"):
        self.folder = Path(folder)
        self.processed_marker = processed_marker

    def fetch_new(self) -> Iterator[RawDocument]:
        self.folder.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.folder.glob("*.pdf")):
            marker = path.with_suffix(path.suffix + self.processed_marker)
            if marker.exists():
                continue
            yield RawDocument(filename=path.name, content=path.read_bytes(), origin="manual")
            marker.touch()

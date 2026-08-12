from dataclasses import dataclass

from ..extraction.base import RawItem
from .models import ProviderItem
from .store import MatchStore, normalize_text


@dataclass
class MatchOutcome:
    item: RawItem
    concept_id: str | None
    candidates: list[ProviderItem]

    @property
    def resolved(self) -> bool:
        return self.concept_id is not None


def match_items(items: list[RawItem], cuit: str, catalog: list[ProviderItem], store: MatchStore) -> list[MatchOutcome]:
    """Intenta resolver cada linea de la factura a un item de compra de Eiffel.

    Orden de resolucion:
    1. Una eleccion humana previa para este mismo proveedor + texto (MatchStore).
    2. Coincidencia exacta de texto contra el catalogo de ese proveedor.
    3. Sin resolver: queda para revision humana, con las opciones de ese proveedor.
    """
    provider_catalog = [entry for entry in catalog if entry.cuit == cuit]
    by_description = {normalize_text(entry.description): entry for entry in provider_catalog}

    outcomes = []
    for item in items:
        remembered = store.get(cuit, item.detail)
        if remembered is not None:
            outcomes.append(MatchOutcome(item=item, concept_id=remembered, candidates=provider_catalog))
            continue

        exact_match = by_description.get(normalize_text(item.detail))
        if exact_match is not None:
            outcomes.append(MatchOutcome(item=item, concept_id=exact_match.concept_id, candidates=provider_catalog))
            continue

        outcomes.append(MatchOutcome(item=item, concept_id=None, candidates=provider_catalog))

    return outcomes

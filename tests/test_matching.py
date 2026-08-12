from facturas.extraction.base import RawItem
from facturas.matching.engine import match_items
from facturas.matching.models import ProviderItem
from facturas.matching.store import MatchStore, normalize_text


def _catalog() -> list[ProviderItem]:
    return [
        ProviderItem(concept_id="1", description="Papel higienico", cuit="30-1-1", provider_name="Proveedor A"),
        ProviderItem(concept_id="2", description="Rollo de cocina", cuit="30-1-1", provider_name="Proveedor A"),
        ProviderItem(concept_id="9", description="Otra cosa", cuit="30-2-2", provider_name="Proveedor B"),
    ]


def test_normalize_text_ignores_case_and_extra_spaces():
    assert normalize_text("  Papel   Higienico ") == "PAPEL HIGIENICO"


def test_exact_match_resolves_automatically(tmp_path):
    store = MatchStore(tmp_path / "matches.json")
    items = [RawItem(detail="papel higienico", unit_price=10, total=10)]

    outcomes = match_items(items, cuit="30-1-1", catalog=_catalog(), store=store)

    assert outcomes[0].resolved
    assert outcomes[0].concept_id == "1"


def test_unmatched_item_leaves_provider_only_candidates(tmp_path):
    store = MatchStore(tmp_path / "matches.json")
    items = [RawItem(detail="algo nuevo", unit_price=10, total=10)]

    outcomes = match_items(items, cuit="30-1-1", catalog=_catalog(), store=store)

    assert not outcomes[0].resolved
    candidate_ids = {c.concept_id for c in outcomes[0].candidates}
    assert candidate_ids == {"1", "2"}  # sin el item del proveedor B


def test_remembered_choice_resolves_next_time(tmp_path):
    store = MatchStore(tmp_path / "matches.json")
    items = [RawItem(detail="algo nuevo", unit_price=10, total=10)]

    store.set("30-1-1", "algo nuevo", "2")
    outcomes = match_items(items, cuit="30-1-1", catalog=_catalog(), store=store)

    assert outcomes[0].resolved
    assert outcomes[0].concept_id == "2"

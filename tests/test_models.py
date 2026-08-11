from datetime import date

from facturas.models import ItemServiceExpenseInput, ServiceExpenseInput


def _minimal_expense() -> ServiceExpenseInput:
    return ServiceExpenseInput(
        document_type="FC",
        document_letter="A",
        document_code="01",
        number="0014-01466684",
        date=date(2026, 8, 4),
        accountable_date=date(2026, 8, 4),
        cuit="30-51973911-5",
        name="Equifax Argentina S.A.",
        net_amount=35166.19,
        total=44625.90,
        items=[
            ItemServiceExpenseInput(
                detail="Abono Mensual Interactive Reports",
                quantity=1,
                unit_price=35166.19,
                vat_aliquot=21,
                total=35166.19,
            )
        ],
    )


def test_serializes_with_boolfy_field_names():
    payload = _minimal_expense().model_dump(by_alias=True)
    assert payload["comprobante_tipo"] == "FC"
    assert payload["emisor_cuit"] == "30-51973911-5"
    assert payload["items"][0]["cuenta_contable"] is None
    assert payload["importe_total"] == 44625.90


def test_roundtrips_from_boolfy_shaped_json():
    original = _minimal_expense()
    payload = original.model_dump(by_alias=True)
    rebuilt = ServiceExpenseInput.model_validate(payload)
    assert rebuilt == original

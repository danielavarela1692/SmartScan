from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class AddressInput(Model):
    address_type: str = Field(default="", alias="Name")
    street: str = Field(default="", alias="Street")
    state: str = Field(default="", alias="State")
    country: str = Field(default="", alias="Country")
    postal_code: str = Field(default="", alias="ZipCode")


class ItemServiceExpenseInput(Model):
    concept_id: Optional[str] = Field(default=None, alias="cuenta_contable")
    detail: str = Field(alias="detalle")
    quantity: float = Field(alias="cantidad")
    unit_price: float = Field(alias="precio_unitario")
    vat_aliquot: float = Field(default=0, alias="alicuota_iva")
    discount: float = Field(default=0, alias="descuento")
    total: float = Field(alias="total")


class ImpuestoInput(Model):
    concept_id: Optional[str] = Field(default=None, alias="cuenta_contable")
    tax: str = Field(alias="impuesto")
    aliquot: float = Field(alias="alicuota")
    amount: float = Field(alias="importe")


class PercepcionInput(Model):
    concept_id: Optional[str] = Field(default=None, alias="cuenta_contable")
    perception: str = Field(alias="percepcion")
    jurisdiction: str = Field(alias="jurisdiccion")
    aliquot: float = Field(alias="alicuota")
    amount: float = Field(alias="importe")


class OtroCargoInput(Model):
    concept_id: Optional[str] = Field(default=None, alias="cuenta_contable")
    name: str = Field(alias="cargo")
    amount: float = Field(alias="importe")


class ComprobanteFinalInput(Model):
    concept: str = Field(alias="concepto")
    number: str = Field(alias="numero")
    expiration_date: date = Field(alias="vencimiento_fecha")


class RuleInput(Model):
    rule: int = Field(alias="Rule")
    name: str = Field(alias="Name")
    passed: bool = Field(alias="Pass")


class TraceInput(Model):
    user: str = Field(default="", alias="User")
    date: date = Field(alias="Date")
    state: str = Field(alias="State")
    comment: Optional[str] = Field(default=None, alias="Comment")


class ServiceExpenseInput(Model):
    identifier: Optional[str] = Field(default=None, alias="Identifier")
    state: Optional[str] = Field(default=None, alias="State")
    process: Optional[str] = Field(default=None, alias="Process")

    document_type: str = Field(alias="comprobante_tipo")
    document_letter: str = Field(alias="comprobante_letra")
    document_code: str = Field(alias="comprobante_codigo")
    number: str = Field(alias="comprobante_numero")
    date: date = Field(alias="comprobante_fecha")
    accountable_date: date = Field(alias="comprobante_fecha_contable")

    cuit: str = Field(alias="emisor_cuit")
    fantasy_name: Optional[str] = Field(default=None, alias="emisor_nombre_fantasia")
    name: str = Field(alias="emisor_nombre")
    address: Optional[AddressInput] = Field(default=None, alias="emisor_direccion")

    currency: str = Field(default="ARS", alias="moneda")
    exchange_rate: float = Field(default=1.0, alias="cotizacion")
    discount: float = Field(default=0, alias="descuento")
    net_amount: float = Field(alias="importe_neto")
    total: float = Field(alias="importe_total")

    items: list[ItemServiceExpenseInput] = Field(default_factory=list, alias="items")
    taxes: list[ImpuestoInput] = Field(default_factory=list, alias="impuestos")
    perceptions: list[PercepcionInput] = Field(default_factory=list, alias="percepciones")
    other_charges: list[OtroCargoInput] = Field(default_factory=list, alias="otros_cargos")
    final_receipt: list[ComprobanteFinalInput] = Field(default_factory=list, alias="comprobante_final")

    deeplink: Optional[str] = Field(default=None, alias="deeplink")
    rules: list[RuleInput] = Field(default_factory=list, alias="rules")
    traces: list[TraceInput] = Field(default_factory=list, alias="traces")

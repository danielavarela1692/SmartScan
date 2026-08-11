from dataclasses import dataclass, field
from typing import Optional

from pydantic import ValidationError

from .classification import DocumentKind, classify
from .extraction import RawExtraction, extract_structured, get_ocr_extractor
from .ingestion import RawDocument, Source
from .models import ComprobanteFinalInput, ItemServiceExpenseInput, ServiceExpenseInput


@dataclass
class ExtractionResult:
    document: RawDocument
    raw: RawExtraction
    service_expense: Optional[ServiceExpenseInput] = None
    errors: list[str] = field(default_factory=list)


def extract_raw(document: RawDocument) -> RawExtraction:
    kind = classify(document.content)
    if kind is DocumentKind.STRUCTURED_PDF:
        return extract_structured(document.content)
    return get_ocr_extractor().extract(document.content)


def to_service_expense(raw: RawExtraction) -> ServiceExpenseInput:
    # cuenta_contable de cada item queda sin resolver: eso es trabajo de la fase 2.
    items = [
        ItemServiceExpenseInput(
            detail=item.detail,
            quantity=item.quantity,
            unit_price=item.unit_price,
            vat_aliquot=item.vat_aliquot,
            total=item.total,
        )
        for item in raw.items
    ]

    final_receipt = []
    if raw.cae and raw.cae_expiration:
        final_receipt.append(
            ComprobanteFinalInput(concept="CAE", number=raw.cae, expiration_date=raw.cae_expiration)
        )

    return ServiceExpenseInput(
        document_type=raw.document_type or "FC",
        document_letter=raw.document_letter or "",
        document_code=raw.document_code or "",
        number=raw.number or "",
        date=raw.issue_date,
        accountable_date=raw.issue_date,
        cuit=raw.cuit or "",
        name=raw.name or "",
        fantasy_name=raw.fantasy_name,
        currency=raw.currency,
        exchange_rate=raw.exchange_rate,
        net_amount=raw.net_amount or 0,
        total=raw.total or 0,
        items=items,
        final_receipt=final_receipt,
    )


def process_document(document: RawDocument) -> ExtractionResult:
    raw = extract_raw(document)

    missing = []
    if not raw.cuit:
        missing.append("no se encontro el CUIT del emisor")
    if not raw.number:
        missing.append("no se encontro el numero de comprobante")
    if missing:
        return ExtractionResult(document=document, raw=raw, errors=missing)

    try:
        service_expense = to_service_expense(raw)
        return ExtractionResult(document=document, raw=raw, service_expense=service_expense)
    except ValidationError as exc:
        errors = [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()]
        return ExtractionResult(document=document, raw=raw, errors=errors)


def run(source: Source) -> list[ExtractionResult]:
    return [process_document(document) for document in source.fetch_new()]

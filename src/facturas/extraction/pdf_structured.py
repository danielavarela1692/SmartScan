import io
import re
from datetime import date, datetime

from pypdf import PdfReader

from .base import RawExtraction, RawItem

CUIT_RE = re.compile(r"C\.?U\.?I\.?T\.?:?\s*(\d{2}-?\d{8}-?\d)")
# Respaldo: algunos comprobantes (ej. resumenes bancarios) muestran el CUIT
# solo, sin la palabra "CUIT" adelante. Se usa solo si CUIT_RE no encontro nada.
CUIT_BARE_RE = re.compile(r"\b(\d{2}-\d{8}-\d)\b")
DOCUMENT_LETTER_RE = re.compile(r"FACTURA\s+([ABM])\b", re.IGNORECASE)
DOCUMENT_CODE_RE = re.compile(r"(?:C[oó]digo|COD)\.?:?\s*(\d+)", re.IGNORECASE)
NUMBER_RE = re.compile(r"N(?:ro|[°ºO])?\.?:?\s*(\d{4,5}\s*-\s*\d{6,8})", re.IGNORECASE)
DATE_RE = re.compile(r"(\d{2})[/\-\s](\d{2})[/\-\s](\d{2}(?:\d{2})?)")
CAE_RE = re.compile(r"C\.?A\.?E\.?:?\s*(\d{14})")
CAE_EXPIRATION_RE = re.compile(
    r"(?:Vto\.?|FECHA\s+VENC)\.?\s*C\.?A\.?E\.?:?\s*(\d{2}/\d{2}/\d{2}(?:\d{2})?)", re.IGNORECASE
)
TOTAL_RE = re.compile(r"\bTOTAL\b\s+([\d.,]+)")
# El total real suele ser el ultimo numero seguido de "$" en el bloque de
# totales (a veces hay varios "$" en esa linea: subtotal, IVA, total...). Se
# usa la ULTIMA coincidencia, no la primera - ver donde se llama mas abajo.
TOTAL_CURRENCY_RE = re.compile(r"([\d.,]+)\s*\$")

# Mapeo de codigo de comprobante AFIP -> letra, para cuando la letra no
# aparece como texto (en muchas facturas reales es un grafico/imagen, no texto).
CODE_TO_LETTER = {"01": "A", "06": "B", "11": "C", "51": "M"}

# Best-effort: la razon social del emisor suele venir en la linea siguiente al
# codigo de comprobante (COD:xx), aunque haya mas texto (ej. la fecha) en esa
# misma linea antes del salto. Igual que el resto de estos regex, especifico
# al formato visto hasta ahora.
NAME_RE = re.compile(r"COD:?\s*\d+.*\n(.+)", re.IGNORECASE)

# Best-effort: "<cantidad> <codigo> <descripcion>   <precio_unitario>  <total>" en una sola linea.
# Como con el resto de los regex de este archivo, es especifico al formato de factura visto
# hasta ahora y va a necesitar ajustes cuando aparezcan facturas de otros proveedores.
ITEM_LINE_RE = re.compile(
    r"^\s*(\d+)\s+(\S+)\s+(.+?)\s{2,}([\d.,]+)\s+([\d.,]+)\s*$"
)


def _parse_ar_number(raw: str) -> float:
    """No todas las facturas usan el mismo formato: unas escriben los
    decimales con coma (22858,30) y otras con punto (493407.68). Se detecta
    cual es el separador decimal en vez de asumir siempre el formato argentino."""
    raw = raw.strip()
    has_comma = "," in raw
    has_dot = "." in raw

    if has_comma and has_dot:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif has_comma:
        raw = raw.replace(",", ".")
    elif has_dot:
        frac = raw.rpartition(".")[2]
        if len(frac) != 2:
            raw = raw.replace(".", "")

    return float(raw)


def _parse_ar_date(raw: str) -> date:
    normalized = raw.replace("-", "/").replace(" ", "/")
    day, month, year = normalized.split("/")
    if len(year) == 2:
        year = "20" + year
    return datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y").date()


def _extract_items(text: str) -> list[RawItem]:
    items = []
    for line in text.splitlines():
        match = ITEM_LINE_RE.match(line)
        if not match:
            continue
        quantity_raw, _code, detail, unit_price_raw, total_raw = match.groups()
        items.append(
            RawItem(
                detail=detail.strip(),
                quantity=_parse_ar_number(quantity_raw),
                unit_price=_parse_ar_number(unit_price_raw),
                total=_parse_ar_number(total_raw),
            )
        )
    return items


def extract_structured(pdf_bytes: bytes) -> RawExtraction:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    cuit_match = CUIT_RE.search(text) or CUIT_BARE_RE.search(text)
    letter_match = DOCUMENT_LETTER_RE.search(text)
    code_match = DOCUMENT_CODE_RE.search(text)
    number_match = NUMBER_RE.search(text)
    date_match = DATE_RE.search(text)
    cae_match = CAE_RE.search(text)
    cae_expiration_match = CAE_EXPIRATION_RE.search(text)
    name_match = NAME_RE.search(text)

    currency_matches = list(TOTAL_CURRENCY_RE.finditer(text))
    total_match = currency_matches[-1] if currency_matches else TOTAL_RE.search(text)

    document_code = code_match.group(1).zfill(2) if code_match else None
    document_letter = letter_match.group(1) if letter_match else CODE_TO_LETTER.get(document_code)

    return RawExtraction(
        cuit=cuit_match.group(1) if cuit_match else None,
        name=name_match.group(1).strip() if name_match else None,
        document_type="FC",
        document_letter=document_letter,
        document_code=document_code,
        number=re.sub(r"\s+", "", number_match.group(1)) if number_match else None,
        issue_date=_parse_ar_date(date_match.group(0)) if date_match else None,
        total=_parse_ar_number(total_match.group(1)) if total_match else None,
        cae=cae_match.group(1) if cae_match else None,
        cae_expiration=(
            _parse_ar_date(cae_expiration_match.group(1)) if cae_expiration_match else None
        ),
        items=_extract_items(text),
        raw_text=text,
    )

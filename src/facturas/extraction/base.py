from datetime import date
from typing import Optional

from pydantic import BaseModel


class RawItem(BaseModel):
    detail: str
    quantity: float = 1
    unit_price: float
    vat_aliquot: float = 0
    total: float


class RawExtraction(BaseModel):
    cuit: Optional[str] = None
    name: Optional[str] = None
    fantasy_name: Optional[str] = None
    document_type: Optional[str] = None
    document_letter: Optional[str] = None
    document_code: Optional[str] = None
    number: Optional[str] = None
    issue_date: Optional[date] = None
    net_amount: Optional[float] = None
    total: Optional[float] = None
    currency: str = "ARS"
    exchange_rate: float = 1.0
    cae: Optional[str] = None
    cae_expiration: Optional[date] = None
    items: list[RawItem] = []
    raw_text: str = ""

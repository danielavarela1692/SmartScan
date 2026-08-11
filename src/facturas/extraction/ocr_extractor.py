from abc import ABC, abstractmethod

from ..config import settings
from .base import RawExtraction


class OCRExtractor(ABC):
    @abstractmethod
    def extract(self, pdf_bytes: bytes) -> RawExtraction: ...


class NotConfiguredOCRExtractor(OCRExtractor):
    def extract(self, pdf_bytes: bytes) -> RawExtraction:
        raise RuntimeError(
            "No hay proveedor de OCR configurado. Elegi uno en OCR_PROVIDER "
            "(azure o google) y completa las credenciales en .env."
        )


class AzureDocumentIntelligenceExtractor(OCRExtractor):
    def __init__(self, endpoint: str, key: str):
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        self.client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))

    def extract(self, pdf_bytes: bytes) -> RawExtraction:
        raise NotImplementedError(
            "Falta mapear la respuesta de Document Intelligence a RawExtraction "
            "una vez que haya facturas escaneadas reales para probar."
        )


def get_ocr_extractor() -> OCRExtractor:
    if settings.ocr_provider == "azure":
        return AzureDocumentIntelligenceExtractor(
            settings.azure_document_intelligence_endpoint,
            settings.azure_document_intelligence_key,
        )
    return NotConfiguredOCRExtractor()

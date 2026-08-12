from pydantic import BaseModel


class ProviderItem(BaseModel):
    """Un item de compra habilitado para un proveedor puntual en Eiffel."""

    concept_id: str
    description: str
    cuit: str
    provider_name: str

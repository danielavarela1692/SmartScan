import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import requests

from .models import ProviderItem


class ItemsCatalogClient(ABC):
    @abstractmethod
    def get_items(self) -> list[ProviderItem]:
        """Devuelve el catalogo completo de items de compra, de todos los proveedores."""


class EiffelApiClient(ItemsCatalogClient):
    """Cliente real contra GrabacionDePedidos.API (login + GET /api/Expense/items)."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._token: Optional[str] = None

    def _login(self) -> str:
        response = requests.post(
            f"{self.base_url}/api/Auth/login",
            json={"username": self.username, "password": self.password},
            timeout=30,
        )
        response.raise_for_status()
        self._token = response.json()["token"]
        return self._token

    def get_items(self) -> list[ProviderItem]:
        token = self._token or self._login()
        response = requests.get(
            f"{self.base_url}/api/Expense/items",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        response.raise_for_status()
        return [
            ProviderItem(
                concept_id=row["idItemDeCompra"],
                description=row["descripcion"],
                cuit=row["cuit"],
                provider_name=row["proveedor"],
            )
            for row in response.json()
        ]


class FixtureItemsCatalogClient(ItemsCatalogClient):
    """Catalogo de prueba leido de un JSON local, para poder probar el motor de
    matching sin credenciales reales de la API (todavia no las tenemos)."""

    def __init__(self, fixture_path: Path):
        self.fixture_path = fixture_path

    def get_items(self) -> list[ProviderItem]:
        data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        return [ProviderItem(**row) for row in data]


def get_items_catalog_client(settings) -> ItemsCatalogClient:
    if settings.eiffel_api_base_url:
        return EiffelApiClient(
            base_url=settings.eiffel_api_base_url,
            username=settings.eiffel_api_username,
            password=settings.eiffel_api_password,
        )
    return FixtureItemsCatalogClient(Path(settings.eiffel_items_fixture))

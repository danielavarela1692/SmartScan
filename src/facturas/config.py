from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    imap_host: str = ""
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"

    ocr_provider: str = "none"
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""
    google_document_ai_processor: str = ""

    cuit_receptor: str = ""

    eiffel_api_base_url: str = ""
    eiffel_api_username: str = ""
    eiffel_api_password: str = ""
    eiffel_items_fixture: str = "fixtures/items_catalog.example.json"

    match_store_path: str = "data/learned_matches.json"
    header_overrides_path: str = "data/header_overrides.json"


settings = Settings()

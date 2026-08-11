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


settings = Settings()

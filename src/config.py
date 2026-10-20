import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    ALLOWED_CHAT_IDS: List[int] = [7150579336]
    GEMINI_API_KEY: str = ""

    WOL_MAC_ADDRESS: str = "24:4B:FE:5C:52:F8"
    WOL_BROADCAST_IP: str = "192.168.1.255"
    WOL_TARGET_IP: str = "192.168.1.92"

    VAULT_PATH: str = "/vault"
    DATABASE_URL: str = "sqlite+aiosqlite:///data/lilo.db"

    GOOGLE_TOKEN_PATH: str = "data/token.json"
    GOOGLE_CREDENTIALS_PATH: str = "data/credentials.json"
    NTFY_TOPIC: str = ""
    NTFY_SERVER: str = "https://ntfy.sh"
    TIMEZONE: str = "America/Santiago"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("ALLOWED_CHAT_IDS", mode="before")
    @classmethod
    def parse_allowed_chats(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v

settings = Settings()

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

VERSION = "0.1.0"
DEFAULT_CONTACT = "+https://github.com/froxily"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HOSHIZORA_", frozen=True)

    ingest_database_url: str
    ll2_base_url: str
    contact: str = DEFAULT_CONTACT

    @property
    def user_agent(self) -> str:
        return f"Hoshizora/{VERSION} ({self.contact})"


class ConfigurationError(Exception):
    pass


def load_settings(**overrides: str) -> Settings:
    try:
        return Settings(**overrides)
    except ValidationError as invalid:
        names = ", ".join(f"HOSHIZORA_{str(error['loc'][0]).upper()}" for error in invalid.errors())
        message = f"Missing or invalid settings: {names}. `just` exports local defaults."
        raise ConfigurationError(message) from invalid

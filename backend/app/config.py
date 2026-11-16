"""
Configuración central de la aplicación.

Usamos `pydantic-settings` para leer las variables de entorno desde el
archivo .env de forma TIPADA y VALIDADA. Esto evita usar os.environ de forma
dispersa y centraliza toda la configuración en un único lugar
(buena práctica de la metodología "12-factor app").
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta a backend/.env, para cargarlo sin importar el directorio actual.
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Esquema tipado de toda la configuración del backend."""

    # --- Google Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    # Modelo alterno si el principal está saturado o sin cuota (vacío = sin respaldo).
    GEMINI_MODEL_RESPALDO: str = ""

    # --- Aplicación ---
    APP_NAME: str = "PlaneAI UdeA"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Reglas de carga académica (motor de validación) ---
    # Reglamento Estudiantil de Pregrado (Acuerdo Superior 1 de 1981):
    # art. 67 -> mínimo 8 créditos; art. 66 -> tiempo completo de 14 a 24.
    CREDITOS_MIN: int = 8
    CREDITOS_MAX: int = 24

    # Lee automáticamente el archivo backend/.env (ruta absoluta _ENV_FILE).
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte la cadena 'a,b,c' de orígenes CORS en una lista de Python."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Devuelve una ÚNICA instancia de Settings (patrón singleton vía caché).

    Gracias a @lru_cache no volvemos a leer el archivo .env en cada
    petición: se lee una sola vez y se reutiliza.
    """
    return Settings()

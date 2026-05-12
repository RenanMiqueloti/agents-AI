"""Configuração centralizada via ``pydantic-settings``.

Substitui ``os.getenv()`` espalhado pelo código por uma classe ``Settings``
única. Carrega de ``.env`` automaticamente; valores podem ser sobrescritos
por env vars do shell.

Padrão LangChain: as keys reais ficam em ``SecretStr`` para evitar
acidente de log. Modelos têm defaults explícitos.

Uso::

    from agents.settings import get_settings
    s = get_settings()
    if s.anthropic_api_key:
        key = s.anthropic_api_key.get_secret_value()
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração consolidada do projeto.

    Lê de ``.env`` no diretório de execução; env vars do shell têm
    precedência. ``extra="ignore"`` permite que outras vars (ex:
    ``OLLAMA_HOST``) coexistam sem erro de validação.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Provider API keys ─────────────────────────────────────────────────
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None

    # ── Langfuse (tracing opt-in) ─────────────────────────────────────────
    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # ── Modelos (overridable) ─────────────────────────────────────────────
    ollama_model: str = "qwen3:8b"
    claude_model: str = "claude-haiku-4-5-20251001"
    openai_model: str = "gpt-5-mini"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna a instância singleton de ``Settings``.

    O cache LRU evita reler ``.env`` em todo acesso. Para forçar reload
    em testes, use ``get_settings.cache_clear()``.
    """
    return Settings()

"""Application configuration."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Ollama remote API settings
    ollama_base_url: str = "https://llm.ainvc.i234.me"
    ollama_api_token: str = "llm_2MeuVYrI4YvvLAO/xLrjf+tbPF45XebpWBFL+5m6ViI="
    ollama_embed_model: str = "embeddinggemma:latest"
    ollama_chat_model: str = "gemma4:26b"

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    rfcs_dir: Path = Path(__file__).resolve().parent.parent / "data" / "rfcs"
    metadata_file: Path = Path(__file__).resolve().parent.parent / "data" / "metadata.json"
    chroma_dir: Path = Path(__file__).resolve().parent.parent / "data" / "chroma"
    graph_dir: Path = Path(__file__).resolve().parent.parent / "data" / "graph"
    embedding_cache_file: Path = (
        Path(__file__).resolve().parent.parent / "data" / "embedding_cache.json"
    )

    # Retrieval parameters
    top_k: int = 5
    similarity_threshold: float = 0.3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

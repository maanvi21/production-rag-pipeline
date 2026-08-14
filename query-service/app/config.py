from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"

    embedding_model: str = "all-MiniLM-L6-v2"

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"

    top_k: int = 5

    class Config:
        env_file = ".env"


settings = Settings()

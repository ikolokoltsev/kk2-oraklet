from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_name: str = "smollm2:135m"
    max_file_size_mb: int = 10
    
    model_config = SettingsConfigDict(env_file=".env")
    
settings = Settings()
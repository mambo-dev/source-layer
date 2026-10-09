from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    jwt_secret:str
    env:str = "development"
    database_url:str
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

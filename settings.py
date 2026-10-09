from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    jwt_secret:str
    env:str = "development"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

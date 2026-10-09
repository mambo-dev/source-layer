from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    jwt_secret:str
    env:str = "development"
    db_name:str
    db_host:str
    db_password:str
    db_port:str
    db_username:str
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

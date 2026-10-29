from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    jwt_secret:str
    env:str = "development"
    db_name:str
    db_host:str
    db_password:str
    db_port:str
    db_username:str
    algorithm:str
    access_token_expire_minutes:int
    ollama_base_url:str
    api_port:int
    ollama_port:int
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

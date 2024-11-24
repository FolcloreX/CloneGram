from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    account_name: str
    phone_number: str
    password: Optional[str]
    api_id: int
    api_hash: str

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False

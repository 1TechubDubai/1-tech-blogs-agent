import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "Autonomous SEO Operations Engine"
    ENVIRONMENT: str = "development"
    
    # Testing Mode
    USE_FILE_STORAGE: bool = False  
    TEST_STORAGE_PATH: str = "./test_output"  
    
    # GCP & Firebase Configuration
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # 🚀 NEW FOR RENDER: Accepts the entire JSON file as a text string
    GOOGLE_APPLICATION_CREDENTIALS_JSON: Optional[str] = None
    CRON_SECRET_KEY: Optional[str] = None
    
    # Made optional so the Docker build phase doesn't crash if it's temporarily missing
    GCP_PROJECT_ID: Optional[str] = None
    
    # Google API Tokens
    RAPIDAPI_KEY: Optional[str] = Field(default=None, env="RAPIDAPI_KEY")
    GOOGLE_CUSTOM_SEARCH_API_KEY: Optional[str] = None
    GOOGLE_CUSTOM_SEARCH_ENGINE_ID: Optional[str] = None
    
    # Gemini / Vertex AI Configs
    VERTEX_AI_LOCATION: str = "us-central1"
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")

    # 🚀 PYDANTIC V2 UPDATE: Replaced `class Config` with `model_config`
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=True,
        extra="ignore" # Prevents crashes if Render injects extra default variables
    )

# Instantiate the settings object
settings = Settings()

if settings.GCP_PROJECT_ID:
    os.environ["GOOGLE_CLOUD_PROJECT"] = settings.GCP_PROJECT_ID
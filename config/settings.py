import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # App
    APP_NAME = "Recrutia"
    VERSION = "1.0.0 (Hackathon Edition)"
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    LOGS_DIR = os.path.join(BASE_DIR, "logs")
    
    # API Keys
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY") # Fallback
    HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
    LINKEDIN_USERNAME = os.getenv("LINKEDIN_USERNAME")
    LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
    
    # Features
    ENABLE_AUDIO = True
    ENABLE_MOCK_DATA = False

settings = Settings()

# Ensure directories exist
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.LOGS_DIR, exist_ok=True)

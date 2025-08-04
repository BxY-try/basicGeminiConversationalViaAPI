import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# External API Keys
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
NEWSAPI_API_KEY = os.getenv("NEWSAPI_API_KEY")

# Validate that the API keys are set
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")
if not OPENWEATHERMAP_API_KEY:
    raise ValueError("OPENWEATHERMAP_API_KEY environment variable is not set")
if not NEWSAPI_API_KEY:
    raise ValueError("NEWSAPI_API_KEY environment variable is not set")
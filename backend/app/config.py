import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"

# Composite score weights (must sum to 1.0)
WEIGHT_SOURCE_REPUTATION = float(os.getenv("WEIGHT_SOURCE_REPUTATION", "0.3"))
WEIGHT_AI_FACT_CHECK = float(os.getenv("WEIGHT_AI_FACT_CHECK", "0.5"))
WEIGHT_LANGUAGE_STYLE = float(os.getenv("WEIGHT_LANGUAGE_STYLE", "0.2"))

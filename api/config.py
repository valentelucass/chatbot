import os
from dotenv import load_dotenv

load_dotenv()

# Chave antiga (pode remover se não for usar mais)
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
HUGGINGFACE_API_URL = os.getenv(
    "HUGGINGFACE_API_URL", 
    "https://api-inference.huggingface.co/models/gpt2"
)

# Nova chave da API da OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
import unicodedata
import re
from datetime import datetime

def normalize_text(text: str) -> str:
    """
    Converte o texto para um formato padronizado e limpo para facilitar a comparação.
    - Transforma em minúsculas.
    - Remove acentos.
    - Remove caracteres especiais (mantém apenas letras, números e espaços).
    """
    if not isinstance(text, str):
        return ""
        
    # Remove acentos
    nfkd_form = unicodedata.normalize('NFKD', text)
    text_without_accents = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    # Converte para minúsculas e remove caracteres não alfanuméricos
    text_lower = text_without_accents.lower()
    text_clean = re.sub(r'[^a-z0-9\s]', '', text_lower)
    
    # Remove espaços duplicados
    return re.sub(r'\s+', ' ', text_clean).strip()

def log_message(message: str):
    """
    Imprime mensagens de log com timestamp.
    Na Vercel, isso aparecerá nos logs da função serverless.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] - {message}")
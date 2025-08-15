from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
# 1. IMPORTE O CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict

# Importa a função principal da lógica do chatbot
from .chatbot import get_response, kb_status, stream_api_response

# Inicializa a aplicação FastAPI
app = FastAPI()

# 2. DEFINA AS ORIGENS PERMITIDAS
# Lista de endereços que podem fazer requisições à sua API
origins = ["*"]

# 3. ADICIONE O MIDDLEWARE À SUA APLICAÇÃO
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],  # Permite todos os métodos (GET, POST, etc)
    allow_headers=["*"],  # Permite todos os cabeçalhos
)

# Define o formato esperado para o corpo da requisição (JSON)
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None  # [{"role": "user"|"assistant", "content": "..."}]
    mode: Optional[str] = None  # "short" (default) | "long"

# Define o formato da resposta (JSON)
class ChatResponse(BaseModel):
    response: str

@app.get("/api")
def read_root():
    """ Rota inicial para verificar se a API está no ar. """
    return {"status": "ok", "message": "API do Chatbot para Estudantes está funcionando!"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_handler(request: ChatRequest):
    """
    Endpoint principal para interagir com o chatbot.
    Recebe uma mensagem e retorna uma resposta.
    """
    user_message = request.message
    history = request.history or []
    bot_answer = get_response(user_message, history=history, mode=request.mode)
    return ChatResponse(response=bot_answer)

@app.post("/api/chat_stream")
async def chat_stream_handler(request: ChatRequest):
    """Endpoint de streaming. Se houver resposta local, envia de uma vez; caso contrário, stream do modelo."""
    gen = stream_api_response(user_input=request.message, history=request.history or [], mode=request.mode)
    return StreamingResponse(gen, media_type="text/plain; charset=utf-8")

@app.get("/api/kb_status")
def kb_status_handler():
    """Retorna informações sobre o carregamento da base local."""
    return kb_status()

# Bloco para permitir a execução local para testes (`python -m api.main`)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
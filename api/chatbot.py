import json
import os
# A nova biblioteca para se comunicar com a API da OpenAI
from openai import OpenAI

# Importa a chave correta e as funções auxiliares
from .config import OPENAI_API_KEY
from .utils import normalize_text, log_message

# O caminho para o JSON continua o mesmo
JSON_FILE_PATH = os.path.join(os.path.dirname(__file__), 'chatbot.json')

# Cache simples com verificação de mtime para recarregar automaticamente
knowledge_base: list[dict] | None = None
knowledge_mtime: float | None = None
# Cache de embeddings por índice da KB
kb_embeddings: list[list[float]] | None = None

def load_knowledge_base() -> list:
    """Carrega a base de conhecimento do arquivo chatbot.json."""
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Se o arquivo não existir ou for inválido, retorna uma lista vazia
        return []

def ensure_kb_loaded():
    """Garante que a base de conhecimento esteja carregada e atualizada."""
    global knowledge_base, knowledge_mtime, kb_embeddings
    try:
        current_mtime = os.path.getmtime(JSON_FILE_PATH)
    except FileNotFoundError:
        current_mtime = None

    if knowledge_mtime != current_mtime:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            knowledge_base = json.load(f)
            knowledge_mtime = current_mtime
            # Invalida cache de embeddings ao recarregar a base
            kb_embeddings = None
            log_message("Base de conhecimento carregada/atualizada.")

# Carrega a base na importação inicial
ensure_kb_loaded()

def get_local_response(user_input: str) -> str | None:
    """Busca por uma resposta na base de conhecimento local."""
    ensure_kb_loaded()
    normalized_input = normalize_text(user_input)
    log_message(f"Buscando resposta local para: '{normalized_input}'")

    # 1) Tentativa de match EXATO
    for item in knowledge_base:
        for keyword in item.get("keywords", []):
            kw_norm = normalize_text(keyword)
            if kw_norm == normalized_input and kw_norm:
                log_message(f"Match exato encontrado: '{keyword}'.")
                return item["response"]

    # 2) Tentativa de match por SUBSTRING (keyword ⊂ input)
    for item in knowledge_base:
        for keyword in item.get("keywords", []):
            kw_norm = normalize_text(keyword)
            if kw_norm and kw_norm in normalized_input:
                log_message(f"Match parcial encontrado: '{keyword}'.")
                return item["response"]
    # 3) Fuzzy matching (similaridade de sequência e sobreposição de tokens)
    try:
        from difflib import SequenceMatcher
        best_score = 0.0
        best_resp = None
        input_tokens = set(normalized_input.split())
        for item in knowledge_base:
            keywords = item.get("keywords", [])
            for kw in keywords:
                kw_norm = normalize_text(kw)
                if not kw_norm:
                    continue
                # Similaridade de sequência
                seq_score = SequenceMatcher(None, kw_norm, normalized_input).ratio()
                # Sobreposição Jaccard simples
                kw_tokens = set(kw_norm.split())
                inter = len(input_tokens & kw_tokens)
                union = len(input_tokens | kw_tokens) or 1
                jacc = inter / union
                score = 0.7 * seq_score + 0.3 * jacc
                if score > best_score:
                    best_score = score
                    best_resp = item.get("response")
        if best_score >= 0.78 and best_resp:
            log_message(f"Match fuzzy encontrado (score={best_score:.2f}).")
            return best_resp
    except Exception as e:
        log_message(f"Fuzzy matching falhou: {e}")

    # 4) Embeddings (opcional) — se houver chave da OpenAI
    try:
        if OPENAI_API_KEY:
            idx = _embedding_best_index(normalized_input)
            if idx is not None:
                return knowledge_base[idx]["response"]
    except Exception as e:
        log_message(f"Embeddings matching falhou: {e}")
    return None

def _get_client() -> OpenAI:
    return OpenAI(api_key=OPENAI_API_KEY)

def _get_embedding(text: str) -> list[float]:
    client = _get_client()
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding

def _cosine(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)) or 1e-8
    nb = math.sqrt(sum(y*y for y in b)) or 1e-8
    return dot / (na * nb)

def _prepare_kb_embeddings():
    global kb_embeddings
    ensure_kb_loaded()
    if not knowledge_base:
        kb_embeddings = []
        return
    if kb_embeddings is not None:
        return
    if not OPENAI_API_KEY:
        kb_embeddings = []
        return
    log_message("Gerando embeddings para a base local...")
    vectors: list[list[float]] = []
    for item in knowledge_base:
        # Texto representativo: keywords concatenadas
        text = "; ".join(item.get("keywords", [])) or item.get("response", "")
        vectors.append(_get_embedding(text))
    kb_embeddings = vectors

def _embedding_best_index(query: str) -> int | None:
    _prepare_kb_embeddings()
    if not kb_embeddings:
        return None
    q_vec = _get_embedding(query)
    best_i, best_s = None, 0.0
    for i, v in enumerate(kb_embeddings):
        s = _cosine(q_vec, v)
        if s > best_s:
            best_s = s
            best_i = i
    if best_s >= 0.82:
        log_message(f"Match por embeddings (cos={best_s:.2f}) no índice {best_i}.")
        return best_i
    return None

def get_api_fallback_response(user_input: str, history: list[dict] | None = None, mode: str | None = None) -> str | None:
    """Chama a API da OpenAI (ChatGPT) como fallback, incluindo contexto recente."""
    if not OPENAI_API_KEY:
        log_message("API da OpenAI não configurada (OPENAI_API_KEY não encontrada).")
        return "Desculpe, meu cérebro externo está offline no momento."

    log_message("Consultando a API da OpenAI...")
    try:
        # 1. Inicializa o cliente da OpenAI com sua chave
        client = _get_client()

        # 2. Monta a requisição para o modelo de chat com histórico
        sys_prompt = (
            "Você é um assistente para estudantes de programação. "
            "Responda SEMPRE de forma concisa e direta (até ~150-200 palavras), "
            "com início, meio e fim claros. Use tópicos curtos quando apropriado e inclua um fechamento rápido. "
            "Evite rodeios, citação excessiva e conteúdo irrelevante. Se a pergunta pedir um resumo, seja ainda mais breve."
        )

        messages = [{"role": "system", "content": sys_prompt}]

        # Anexa até 6 mensagens anteriores (3 pares) mais recentes
        safe_history = history or []
        trimmed = safe_history[-6:]
        for m in trimmed:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        # Mensagem atual do usuário
        messages.append({"role": "user", "content": user_input})

        # 3. Parâmetros por modo + mensagem de sistema
        # Parâmetros de geração por modo
        mode_norm = (mode or "short").lower()
        if mode_norm == "long":
            temperature = 0.3
            max_tokens = 600
            sys_prompt = (
                "Você é um assistente para estudantes de programação. "
                "Responda de forma clara, estruturada e completa, porém objetiva. Use seções e exemplos quando necessário. "
                "Finalize com um resumo curto do que foi respondido."
            )
        else:
            temperature = 0.2
            max_tokens = 300
            sys_prompt = (
                "Você é um assistente para estudantes de programação. "
                "Responda SEMPRE de forma concisa e direta (até ~150-200 palavras), "
                "com início, meio e fim claros. Use tópicos curtos quando apropriado e inclua um fechamento rápido. "
                "Evite rodeios, citação excessiva e conteúdo irrelevante. Se a pergunta pedir um resumo, seja ainda mais breve."
            )

        # Insere a mensagem de sistema no topo
        messages = [{"role": "system", "content": sys_prompt}] + messages

        response = client.chat.completions.create(
            # Modelo atual e econômico
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # 3. Extrai o conteúdo de texto da resposta
        bot_response = response.choices[0].message.content
        return bot_response.strip()

    except Exception as e:
        # Log detalhado no servidor, resposta amigável no cliente
        log_message(f"Erro ao chamar a API da OpenAI: {e}")
        return "Tive um problema temporário ao falar com o modelo de IA. Tente novamente em instantes."

def get_response(user_input: str, history: list[dict] | None = None, mode: str | None = None) -> str:
    """
    Função principal que orquestra a lógica de resposta.
    Prioridade: JSON local -> API externa (OpenAI).
    """
    # 1. Tenta buscar no JSON local
    local_response = get_local_response(user_input)
    if local_response:
        return local_response

    # 2. Se não encontrou, chama a API de fallback da OpenAI
    api_response = get_api_fallback_response(user_input, history=history, mode=mode)
    if api_response:
        return api_response

    # 3. Se tudo falhar, retorna uma mensagem padrão
    return "Desculpe, não consegui entender sua pergunta. Pode tentar reformulá-la?"

def kb_status() -> dict:
    """Retorna informações de diagnóstico sobre a base local."""
    ensure_kb_loaded()
    return {
        "entries_count": len(knowledge_base or []),
        "mtime": knowledge_mtime,
        "json_path": JSON_FILE_PATH,
    }

def stream_api_response(user_input: str, history: list[dict] | None = None, mode: str | None = None):
    """Gerador que realiza streaming do fallback da OpenAI. Se a base local tiver resposta, envia de uma vez."""
    # 1) Tenta base local primeiro
    local = get_local_response(user_input)
    if local:
        yield local
        return

    # 2) Sem chave, não há como fazer streaming do modelo
    if not OPENAI_API_KEY:
        yield "Meu cérebro externo está offline no momento."
        return

    try:
        client = _get_client()
        messages: list[dict] = []
        if history:
            safe_history = history[-6:]
            for m in safe_history:
                role = m.get("role", "user")
                content = m.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_input})

        mode_norm = (mode or "short").lower()
        if mode_norm == "long":
            temperature = 0.3
            max_tokens = 600
            sys_prompt = (
                "Você é um assistente para estudantes de programação. "
                "Responda de forma clara, estruturada e completa, porém objetiva. Use seções e exemplos quando necessário. "
                "Finalize com um resumo curto do que foi respondido."
            )
        else:
            temperature = 0.2
            max_tokens = 300
            sys_prompt = (
                "Você é um assistente para estudantes de programação. "
                "Responda SEMPRE de forma concisa e direta (até ~150-200 palavras), "
                "com início, meio e fim claros. Use tópicos curtos quando apropriado e inclua um fechamento rápido. "
                "Evite rodeios, citação excessiva e conteúdo irrelevante. Se a pergunta pedir um resumo, seja ainda mais breve."
            )
        messages = [{"role": "system", "content": sys_prompt}] + messages

        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
    except Exception as e:
        log_message(f"Erro no streaming: {e}")
        yield "[Falha temporária no streaming]"
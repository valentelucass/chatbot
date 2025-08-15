## Deploy na Vercel

Este projeto está preparado para deploy na Vercel com backend em FastAPI e frontend estático.

### Requisitos
- Python (gerenciado pela Vercel via `@vercel/python`)
- `requirements.txt` no raiz do projeto
- `vercel.json` já configurado
- Variável de ambiente `OPENAI_API_KEY`

### Passos
1. Crie um projeto na Vercel e importe este repositório.
2. Em Settings → Environment Variables, adicione:
   - `OPENAI_API_KEY` (Production/Preview/Development conforme desejar)
3. Deploy.

### Roteamento
- API: `api/main.py` servida por `@vercel/python`.
- Frontend: tudo em `frontend/` servindo assets estáticos.
- Rotas definidas em `vercel.json`:
  - `/api/(.*)` → `api/main.py`
  - `/*.(css|js|png|jpg|jpeg|svg|ico|webp|json)` → `frontend/`
  - fallback `/(.*)` → `frontend/index.html`

### Endpoints úteis
- `POST /api/chat` → endpoint principal do chatbot
- `GET /api/kb_status` → diagnóstico da base local (quantidade, mtime, caminho)

## Desenvolvimento local

### Backend
```bash
python -m api.main
# Servirá em http://127.0.0.1:8000
```

### Frontend
Abra `frontend/index.html` com Live Server (http://127.0.0.1:5500). O frontend detecta ambiente local e chama `http://127.0.0.1:8000/api/chat` automaticamente.

## Variáveis de ambiente
- `OPENAI_API_KEY` → chave da OpenAI usada no fallback do modelo.

## Prioridade da Base Local
A lógica tenta responder primeiro usando `api/chatbot.json` (match exato e por substring). Só chama a OpenAI se não houver resposta local.

## Recursos Implementados
- Auto-reload do `chatbot.json` por mtime.
- Toggle de resposta curta/longa no frontend (enviado como `mode`).
- "Mostrar mais/menos" para respostas longas.
- Endpoint de diagnóstico `GET /api/kb_status`.

### Novidades
- Streaming de respostas: `POST /api/chat_stream` (melhor UX em respostas longas).
- Realce de código com Prism.js no frontend (`frontend/index.html`).
- Correspondência local aprimorada:
  - Exato → Substring → Fuzzy (SequenceMatcher + Jaccard) → Embeddings (OpenAI) opcional.

## Como funciona o matching local
Ordem de tentativa no `api/chatbot.py` → `get_local_response()`:
1. Exato: `normalize_text(input) == normalize_text(keyword)`.
2. Substring: `keyword ∈ input normalizado`.
3. Fuzzy: combinação de similaridade de sequência e sobreposição de tokens (limiar ~0.78).
4. Embeddings (opcional): usa `text-embedding-3-small` para comparar consulta com vetores da KB (limiar cos ~0.82). Cache de embeddings é invalidado ao recarregar a base.

Observação: Embeddings só ativam se `OPENAI_API_KEY` estiver definido.

## Streaming no Frontend
O frontend agora consome `/api/chat_stream` e renderiza o texto incrementalmente; ao final aplica Markdown + Prism.js e o colapso "Mostrar mais/menos".

## Realce de Código (Prism.js)
Incluímos Prism theme Tomorrow e linguagens comuns (JS, TS, Python, Java). Para detectar linguagem, use blocos:

```markdown
```python
print("hello")
```
```

O renderer adiciona `class="language-<lang>"` ao `<code>`.
# Chatbot para Estudantes

Este projeto é um chatbot simples e escalável, projetado para ajudar estudantes com dúvidas sobre programação e outros tópicos de estudo. A arquitetura foi pensada para ser de fácil manutenção, baixo custo e com deploy simplificado na Vercel.

## ✨ Visão Geral da Arquitetura

O projeto é dividido em duas camadas principais:

-   **Frontend**: Uma interface de chat estática construída com HTML, CSS e JavaScript puros. Ela é responsável por exibir a conversa e se comunicar com o backend.
-   **Backend**: Uma API em Python construída com o framework FastAPI. Ela contém a lógica do chatbot, processando as mensagens dos usuários.

### Fluxo de Funcionamento
1.  O usuário envia uma mensagem através do frontend.
2.  O frontend faz uma requisição HTTP POST para o endpoint `/api/chat`.
3.  O backend FastAPI recebe a mensagem.
4.  A lógica do chatbot primeiro busca por uma resposta em uma base de conhecimento local (`chatbot.json`).
5.  Se nenhuma resposta correspondente for encontrada, ele consulta a API da OpenAI (ChatGPT) como fallback.
6.  A resposta é retornada em formato JSON para o frontend, que a exibe na tela.

---

## 🚀 Estrutura de Diretórios

```
chatbot/
│
├── api/
│   ├── main.py             # Entrada da API (FastAPI)
│   ├── chatbot.py          # Módulo de lógica do chatbot
│   ├── chatbot.json        # Base local de conhecimento
│   ├── config.py           # Configurações e variáveis de ambiente
│   ├── utils.py            # Funções auxiliares
│   └── __init__.py         # Marca 'api' como pacote Python
│
├── frontend/
│   ├── index.html          # Estrutura da página de chat
│   ├── style.css           # Estilos visuais
│   └── script.js           # Lógica do cliente (chamadas de API)
│
├── requirements.txt        # Dependências do backend Python
├── vercel.json             # Configuração de deploy para a Vercel
├── .env                    # Variáveis de ambiente (não versionar)
├── .gitignore              # Arquivos/pastas ignorados pelo Git
└── README.md               # Este arquivo
```

---

## 🛠️ Como Executar Localmente

Siga os passos abaixo para testar o projeto na sua máquina.

### Pré-requisitos
-   [Python 3.9+](https://www.python.org/downloads/)
-   Um editor de código (ex: VS Code)
-   Conta na [OpenAI](https://platform.openai.com/) e uma API Key (opcional, apenas para o fallback com ChatGPT).

### Passo a Passo no Terminal

1.  **Clone o repositório (ou crie a pasta e os arquivos):**
    ```bash
    # Se estiver usando git
    git clone <url-do-seu-repositorio>
    cd chatbot
    ```

2.  **Crie e ative um ambiente virtual:**
    Isso isola as dependências do seu projeto.
    ```bash
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # macOS / Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instale as dependências Python:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **(Opcional) Configure as variáveis de ambiente para o fallback (OpenAI):**
    Crie um arquivo chamado `.env` na raiz (`chatbot/`) e adicione sua chave da OpenAI.
    ```
    # .env
    OPENAI_API_KEY="sk-...sua_chave_aqui"
    ```

5.  **Inicie o servidor da API:**
    ```bash
    uvicorn api.main:app --reload
    ```
    -   O servidor estará rodando em `http://127.0.0.1:8000`.
    -   A flag `--reload` reinicia o servidor automaticamente quando você altera o código.

6.  **Abra o frontend:**
    -   Navegue até a pasta `frontend/`.
    -   Abra o arquivo `index.html` diretamente no seu navegador.
    -   **Importante:** Para o `script.js` conseguir chamar a API localmente, você pode precisar de um servidor de arquivos estáticos simples para evitar problemas de CORS. A forma mais fácil é usar a extensão "Live Server" no VS Code.

---

## 🌐 Deploy na Vercel

O deploy deste projeto na Vercel é extremamente simples:

1.  Envie seu projeto para um repositório no GitHub, GitLab ou Bitbucket.
2.  Acesse sua conta na [Vercel](https://vercel.com).
3.  Clique em "Add New..." -> "Project".
4.  Importe o repositório do seu projeto.
5.  A Vercel deve detectar automaticamente que é um projeto Python com FastAPI e usar as configurações do `vercel.json`. Nenhum ajuste é necessário.
6.  **(Opcional) Adicione suas Environment Variables** na aba de configurações do projeto na Vercel (ex: `OPENAI_API_KEY`).
7.  Clique em "Deploy". Pronto!

---

## 📝 Observações importantes

-   **CORS/localhost**: o backend permite origens `http://127.0.0.1:5500` e `http://localhost:5500`. Use um servidor estático (ex.: extensão Live Server no VS Code) para abrir `frontend/index.html` durante o desenvolvimento.
-   **Endpoint dinâmico no frontend**: `frontend/script.js` seleciona automaticamente o endpoint da API. Em localhost usa `http://127.0.0.1:8000/api/chat`; em produção usa o caminho relativo `/api/chat`.
-   **.gitignore**: já incluso para evitar versionar `.venv/`, `.env`, caches, logs e artefatos de build.
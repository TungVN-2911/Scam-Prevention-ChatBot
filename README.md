# 🛡️ Scam-Prevention-ChatBot

Trợ lý cá nhân bằng tiếng Việt giúp người dùng **nhận diện, phòng tránh và xử lý lừa đảo trực tuyến**. Dự án xây dựng cho hackathon **AI Riser Vietnam (#BuildWithGoogleAI)**.

## Tính năng

- **💬 Chat RAG** — trả lời dựa trên knowledge base thật (23 hình thức lừa đảo, hướng dẫn phòng tránh/khắc phục, văn bản pháp luật), dùng Gemini + Pinecone + Ollama, có cơ chế chống bịa thông tin (hotline, điều luật, số liệu...).
- **🎯 Quiz** — 40 câu trắc nghiệm tĩnh (4 chủ đề × 10 câu), chấm điểm xác định, cộng XP.
- **🛡️ Scam of the Day** — mỗi ngày hiển thị 1 hình thức lừa đảo (chọn deterministic theo ngày, cùng ngày mọi người thấy giống nhau).
- **🕵️ Scam Detective** — mini-game: đọc 1 tình huống thật, tìm các dấu hiệu đáng ngờ, chấm điểm xác định (không qua AI), cộng XP.
- **Lưu lịch sử chat & nhiều cuộc trò chuyện** — tạo session khi gửi tin nhắn đầu tiên (lazy), có thể tạo mới/chuyển qua lại giữa các cuộc trò chuyện.
- **Learning Progress (XP)** — độc lập hoàn toàn với lịch sử chat, không mất khi tạo cuộc trò chuyện mới hay chuyển phiên.

## Kiến trúc

```
frontend/   Streamlit — chat UI + Quiz + Scam of the Day + Scam Detective
backend/    FastAPI
  app/api/routes/     endpoint HTTP (auth, chat, quiz, scam_of_day, detective, session, learning_progress, speech)
  app/orchestrator/   phân loại ý định (rule-based) + điều phối RAG/LLM/MCP
  app/llm_gateway/    gọi Gemini, có system prompt chống hallucination
  app/rag_engine/     embedding (Ollama) + tìm kiếm vector (Pinecone)
  app/scam_connector/ đọc dữ liệu hình thức lừa đảo/hotline tĩnh
  app/mcp/server.py   MCP Server standalone (Streamable HTTP) — tool cho Gemini gọi, tự verify JWT/RBAC
  app/auth.py                    JWT (HS256) + RBAC (role user/admin)
  app/session_store.py           lưu trữ hội thoại (SQL Server), cách ly theo user
  app/learning_progress_store.py lưu trữ XP (SQL Server, độc lập với hội thoại)
data/               câu hỏi quiz, case Scam Detective, hotline, báo cáo chờ duyệt
knowledge_base/     nguồn tri thức gốc (.md, .json) + script ingest vào Pinecone
```

## Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Backend | FastAPI |
| Frontend | Streamlit |
| LLM | Google Gemini (`gemini-3.5-flash-lite`) |
| Tool cho Gemini | MCP (Streamable HTTP), JWT xác thực + RBAC deny-by-default |
| Vector DB | Pinecone |
| Embedding | Ollama (`nomic-embed-text`, chạy local) |
| Database | SQL Server (qua `pyodbc`) |
| Auth | JWT (`PyJWT`) + `bcrypt` |
| Test | pytest |

## Yêu cầu trước khi chạy

- Python 3.11+
- [Ollama](https://ollama.com) đã cài và đang chạy local, đã pull model `nomic-embed-text` (`ollama pull nomic-embed-text`)
- 1 SQL Server instance có thể kết nối được, đã cài driver **ODBC Driver 17/18 for SQL Server**
- API key: Google Gemini, Pinecone

## Cài đặt

### 1. Cấu hình `.env`

Copy `.env.example` thành `.env` ở thư mục gốc, điền các giá trị thật:

```
GEMINI_API_KEY=...
PINECONE_API_KEY=...
PINECONE_INDEX=scam-prevention-knowledge-base
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
SQL_SERVER_CONNECTION_STRING=Driver={ODBC Driver 17 for SQL Server};Server=...;Database=...;UID=...;PWD=...;TrustServerCertificate=yes
BACKEND_URL=http://localhost:8000
```

### 2. Tạo bảng trong SQL Server

Chạy đoạn SQL sau trên database đã trỏ trong connection string ở trên:

```sql
CREATE TABLE users (
    username        VARCHAR(64)   NOT NULL PRIMARY KEY,
    password_hash   VARCHAR(256)  NOT NULL,
    role            VARCHAR(16)   NOT NULL DEFAULT 'user',
    created_at      DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE chat_sessions (
    session_id  VARCHAR(64)   NOT NULL PRIMARY KEY,
    username    VARCHAR(64)   NULL,
    created_at  DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at  DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE chat_messages (
    id            INT IDENTITY(1,1) PRIMARY KEY,
    session_id    VARCHAR(64)     NOT NULL,
    role          VARCHAR(16)     NOT NULL,
    content       NVARCHAR(MAX)   NOT NULL,
    sources_json  NVARCHAR(MAX)   NULL,
    created_at    DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_chat_messages_session FOREIGN KEY (session_id)
        REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);
CREATE INDEX IX_chat_messages_session_id ON chat_messages(session_id);

CREATE TABLE learning_progress (
    user_key    VARCHAR(64)   NOT NULL PRIMARY KEY,
    xp          INT           NOT NULL DEFAULT 0,
    created_at  DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at  DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE quiz_attempts (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    user_key          VARCHAR(64)     NOT NULL,
    topic             VARCHAR(64)     NOT NULL,
    correct_count     INT             NOT NULL,
    total_questions   INT             NOT NULL,
    xp_earned         INT             NOT NULL,
    answers_json      NVARCHAR(MAX)   NULL,
    created_at        DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE INDEX IX_quiz_attempts_user_key ON quiz_attempts(user_key);

CREATE TABLE detective_attempts (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    user_key          VARCHAR(64)     NOT NULL,
    case_id           VARCHAR(64)     NOT NULL,
    correct_count     INT             NOT NULL,
    total_expected    INT             NOT NULL,
    xp_earned         INT             NOT NULL,
    result_json       NVARCHAR(MAX)   NULL,
    created_at        DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE INDEX IX_detective_attempts_user_key ON detective_attempts(user_key);
```

### 3. Ingest knowledge base vào Pinecone (chạy 1 lần)

```bash
cd knowledge_base
python ingest.py
```

### 4. Chạy backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Kiểm tra: `http://localhost:8000/health` → `{"status": "ok"}`. Xem toàn bộ API tại `http://localhost:8000/docs`.

### 5. Chạy MCP Server (tuỳ chọn — Chat vẫn trả lời được nếu bỏ qua, chỉ không gọi được tool)

```bash
cd backend
python -m app.mcp.server
```

Mặc định chạy ở `http://127.0.0.1:8020/mcp` (khớp `MCP_SERVER_URL` trong `.env`). Nếu MCP Server không chạy, Chat tự động fallback về trả lời chỉ dựa trên RAG, không gọi được tool `search_scam_patterns`/`list_hotlines`.

### 6. Chạy frontend

```bash
cd frontend
streamlit run app.py
```

## Chạy test

```bash
cd backend
pytest
```

Các test liên quan SQL Server (session/learning progress) sẽ tự `skip` nếu `.env` chưa cấu hình `SQL_SERVER_CONNECTION_STRING`.

## Giới hạn đã biết

- Chất lượng embedding của `nomic-embed-text` trên corpus nhỏ này chưa được hiệu chỉnh tốt, retrieval đôi khi chưa lấy đúng ngữ cảnh sát nhất.
- Gemini free tier giới hạn 20 request/ngày.
- Intent detection dựa trên khớp cụm từ (rule-based), có thể không nhận đúng ý định với cách diễn đạt lạ.
- `data/pending_reports.json` là file JSON đơn giản, ghi theo kiểu đọc-sửa-ghi (có khoá trong 1 process để tránh mất dữ liệu khi 2 request trùng lúc) — chưa an toàn nếu chạy nhiều worker process cùng lúc.

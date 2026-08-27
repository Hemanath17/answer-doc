# AnswerDoc

A RAG-powered document assistant that lets you chat with your documents, websites, YouTube videos, and more.

🔗 **Live demo → [answer-doc.vercel.app](https://answer-doc.vercel.app)**

---

## What it does

You add a source — a PDF, a web link, a YouTube video, or just paste some text — and then ask questions about it. The app finds the most relevant parts of your content, and answers using only what's actually in the document. No hallucinations, no outside knowledge.

If you ask to "show" something, it will pull the relevant image straight from the source. If the content has a table, it reads that too.

---

## How it works

1. **Ingest** — your source gets parsed, split into chunks, and embedded as vectors
2. **Retrieve** — when you ask a question, the most relevant chunks are pulled from the vector database
3. **Rerank** — a cross-encoder model re-scores the candidates for better precision
4. **Generate** — GPT-4o mini streams the answer token by token, citing the exact pages

---

## Tech stack

**Frontend**
- React + Vite
- Streaming SSE responses (no page reload, tokens appear as they're generated)
- Dark / light theme

**Backend**
- FastAPI (Python)
- OpenAI — embeddings (`text-embedding-3-small`) + generation (`gpt-4o-mini`)
- Pinecone — vector storage and similarity search
- Cohere — reranking
- Cloudinary — image storage for PDF images
- Trafilatura — web page content extraction
- YouTube Transcript API — YouTube video ingestion

---

## Supported sources

| Type | How to add |
|---|---|
| PDF / TXT / CSV | Upload via sidebar |
| Web page | Paste URL |
| YouTube video | Paste video link |
| Plain text | Paste directly |

---

## Running locally

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # fill in your keys
python main.py
```

**Frontend**
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

---

## Environment variables

| Variable | What it's for |
|---|---|
| `OPENAI_API_KEY` | Embeddings + generation |
| `PINECONE_API_KEY` | Vector database |
| `PINECONE_INDEX` | Index name |
| `COHERE_API_KEY` | Reranking |
| `CLOUDINARY_CLOUD_NAME` | Image hosting |
| `CLOUDINARY_API_KEY` | Image hosting |
| `CLOUDINARY_API_SECRET` | Image hosting |

# 🏛️ NyayaBot (न्यायबॉट) — Policy-to-Citizen AI Assistant

> **Empowering Indian citizens with clear, jargon-free explanations of government welfare schemes and policies using Google Gemini AI, Retrieval-Augmented Generation (RAG), and Multilingual Translation.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-gemini--3.5--flash--lite-4285F4.svg?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Telegram](https://img.shields.io/badge/Telegram%20Bot-Webhook%20%26%20Polling-2CA5E0.svg?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org)
[![Render](https://img.shields.io/badge/Deployable%20on-Render.com-46E3B7.svg?style=for-the-badge&logo=render&logoColor=white)](https://render.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

---

## 📑 Table of Contents

1. [🌟 Project Overview](#-project-overview)
2. [🎯 The Problem NyayaBot Solves](#-the-problem-nyayabot-solves)
3. [⚡ Core Capabilities & Key Features](#-core-capabilities--key-features)
4. [🛠️ Tech Stack & Architecture](#️-tech-stack--architecture)
5. [🤖 AI Providers — Gemini & Anthropic](#-ai-providers--gemini--anthropic)
6. [🧠 RAG Pipeline — Step-by-Step Data Flow](#-rag-pipeline--step-by-step-data-flow)
7. [📂 Project Directory Structure](#-project-directory-structure)
8. [🚀 Installation & Setup Guide](#-installation--setup-guide)
9. [⚙️ Environment Configuration (.env)](#️-environment-configuration-env)
10. [🖥️ Launching the Application (All Modes)](#️-launching-the-application-all-modes)
11. [📱 Telegram Bot Integration & Commands](#-telegram-bot-integration--commands)
12. [📡 REST API Reference](#-rest-api-reference)
13. [📚 Expanding the Knowledge Base](#-expanding-the-knowledge-base)
14. [🌐 Multilingual Support & Indian Languages](#-multilingual-support--indian-languages)
15. [☁️ Production Deployment on Render.com](#️-production-deployment-on-rendercom)
16. [❓ Troubleshooting & FAQ](#-troubleshooting--faq)
17. [📜 License & Data Sources](#-license--data-sources)

---

## 🌟 Project Overview

In India, the Central and State Governments run hundreds of welfare schemes providing financial aid, free healthcare, affordable housing, pensions, educational scholarships, and farmer subsidies.

However, millions of eligible citizens **miss out on their rightful benefits** every year because:
1. Government guidelines are published as **50-to-100-page dense legal PDF documents**.
2. The language is packed with **bureaucratic jargon** that ordinary citizens cannot understand.
3. Information is scattered across **hundreds of different departmental websites**.
4. Many citizens cannot read English or formal Hindi and only understand their regional language.

### 💡 What NyayaBot Does

**NyayaBot** is an AI assistant that acts as a free, personal legal-welfare advisor. You can ask it a question in **plain everyday words** (e.g., *"How can I get ₹6,000 as a farmer?"* or in Hindi: *"पीएम किसान के लिए कौन से दस्तावेज़ चाहिए?"*), and NyayaBot will:

- 🔍 **Instantly search** official government policy guidelines using RAG.
- 📋 **Tell you if you qualify** based on land holding, income, or family category.
- 💰 **Explain exact benefit amounts** (e.g., ₹6,000/year, ₹5 lakh health insurance).
- 📑 **List every required document** (Aadhaar card, ration card, land records, bank passbook).
- 📝 **Provide clear step-by-step instructions** on how to apply online or offline.
- 📞 **Give verified helpline numbers and official websites** to protect citizens from fraud.

---

## 🎯 The Problem NyayaBot Solves

```
┌──────────────────────────────────────┬──────────────────────────────────────┐
│ ❌ WITHOUT NYAYABOT                  │ ✅ WITH NYAYABOT                     │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ 50+ page dense PDF documents         │ 3-bullet-point plain summary         │
│ Bureaucratic legal terminology       │ Simple, everyday language            │
│ Unclear eligibility criteria         │ Clear "You are eligible if..."       │
│ Complex multi-portal navigation      │ One-stop conversational search       │
│ Risk of exploitation by middlemen    │ Official helplines & direct links    │
│ Language barrier (English/Hindi only)│ 12 native Indian languages           │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## ⚡ Core Capabilities & Key Features

- 🧠 **Retrieval-Augmented Generation (RAG):** NyayaBot retrieves facts directly from verified policy documents and feeds them to Google Gemini. It never guesses or hallucinates.
- 🤖 **Google Gemini AI (Primary):** Uses `gemini-3.5-flash-lite` by default (configurable via `GEMINI_MODEL`). Ultra-fast, low-latency generation with exponential backoff retry logic (3 attempts: 0.5s → 1s → 2s) for resilience against transient API errors.
- 🔄 **Anthropic Claude Fallback:** If only `ANTHROPIC_API_KEY` is configured (no Gemini key), the system automatically switches to `claude-haiku-4-5-20251001`.
- 🌊 **Word-by-Word Streaming (SSE):** The `/api/chat/stream` endpoint uses Server-Sent Events (SSE) backed by a true async generator (`client.aio.models.generate_content_stream`) to deliver one word per SSE frame for a real-time typing effect in the browser.
- 🌐 **Multilingual Support (12 Indic Languages):** Supports Hindi, Tamil, Bengali, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Urdu, Odia, and English. Input language is auto-detected using zero-latency Unicode script matching. Translation is powered by `deep-translator` with in-memory caching.
- 📄 **Dynamic Document & PDF Uploads:** Upload any official government PDF via the Web UI (📎 button) or directly via Telegram. NyayaBot extracts text using PyMuPDF (`fitz`), chunks it, and adds it to the live TF-IDF index on-the-fly.
- 📱 **Dual-Mode Telegram Bot:** Supports embedded FastAPI **Webhook mode** (for cloud deployment) and standalone **Long Polling mode** (for local development). Includes inline keyboards, scheme quick-access buttons, a typing heartbeat, and Telegram-compatible Markdown formatting.
- 📊 **Analytics Dashboard:** A real-time web dashboard (`/dashboard.html`) showing query volume, popular schemes, language distribution, and backend health status.
- 🌾 **Pre-Loaded Knowledge Base:** Ships with `data/training/training_data.json` (24 KB of structured policy data), covering PM-KISAN, Ayushman Bharat (PM-JAY), PM Awas Yojana, MGNREGA, Ujjwala Yojana, Jan Dhan Yojana, and more.
- 🚀 **Zero-GPU Architecture:** Engineered with lightweight TF-IDF (`scikit-learn`) and NumPy. No FAISS, no GPU, no sentence-transformers — runs smoothly on free-tier CPU instances (Render.com free plan).

---

## 🛠️ Tech Stack & Architecture

| Layer | Technology / Library | Purpose |
|---|---|---|
| **Core AI (Primary)** | `google-genai >= 2.0.0` | Google Gemini LLM (`gemini-3.5-flash-lite`). Structured answers, temperature `0.2`, max 800 output tokens, exponential backoff retry. |
| **Core AI (Fallback)** | `anthropic >= 0.20.0` | Anthropic Claude (`claude-haiku-4-5-20251001`) as secondary LLM if no Gemini key is configured. |
| **Web Framework** | `fastapi >= 0.110.0` | Async REST API server hosting chat, streaming SSE, upload, search, stats, and static frontend endpoints. |
| **ASGI Server** | `uvicorn[standard] >= 0.27.0` | Production-grade ASGI server for async request handling. |
| **Data Validation** | `pydantic >= 2.5.0` | Request/response schema validation and auto-generated Swagger (`/api/docs`) & ReDoc (`/api/redoc`). |
| **Vector Search (RAG)** | `scikit-learn >= 1.4.0` | `TfidfVectorizer` (5,000 features, 1-2 ngrams) + `cosine_similarity` for retrieval. Rebuilt in-memory each startup. |
| **Numeric Operations** | `numpy >= 1.26.0` | Score array sorting and ranking for TF-IDF retrieval results. |
| **PDF Extraction** | `PyMuPDF (fitz) >= 1.23.0` | High-speed text extraction from uploaded government policy PDFs. |
| **Text Translation** | `deep-translator >= 1.11.0` | Google Translate backend for bidirectional Indic language translation with in-memory caching. |
| **Script Detection** | Built-in Unicode ranges | Zero-latency Devanagari, Tamil, Bengali, and Telugu script detection via character range checks. |
| **Telegram Bot** | `python-telegram-bot >= 20.0` | Async bot framework with inline keyboards, `CallbackQueryHandler`, PDF ingestion, and typing heartbeat. |
| **HTTP Client** | `httpx >= 0.26.0` | Async HTTP client for external integrations. |
| **File Upload** | `python-multipart >= 0.0.9` | Multipart form data parsing for PDF upload REST endpoints. |
| **Environment** | `python-dotenv >= 1.0.0` | Loads secrets from `.env` at startup before any module imports. |
| **Frontend** | HTML5, Vanilla CSS3, ES6 JS | Dark-theme glassmorphism UI with ambient orbs, CSS animations, and responsive layout. Uses `marked.js v9` (CDN) for Markdown rendering. |
| **Typography** | Google Fonts | *Playfair Display* (headings), *DM Sans* (body), *DM Mono* (data/stats). |
| **Deployment** | `render.yaml` + `Procfile` | Single-service Render.com free-tier blueprint. One port serves API, Web UI, and Telegram Webhook. |

---

## 🤖 AI Providers — Gemini & Anthropic

### Google Gemini (Primary)

NyayaBot uses **Google Gemini** as its primary AI engine:

- **Default Model:** `gemini-3.5-flash-lite` (overridable via `GEMINI_MODEL` env var)
- **SDK:** `google-genai >= 2.0.0` — uses `client.models.generate_content()` (sync) and `client.aio.models.generate_content_stream()` (async streaming)
- **Retry Logic:** 3 attempts with exponential backoff (`0.5s → 1.0s → 2.0s`) on `503 UNAVAILABLE` or `429 RESOURCE_EXHAUSTED` errors
- **Parameters:** `temperature=0.2`, `max_output_tokens=800`
- **Free Tier:** Available at [Google AI Studio](https://aistudio.google.com/apikey) — no credit card required

### Anthropic Claude (Fallback)

If only `ANTHROPIC_API_KEY` is set (and no Gemini key), the engine automatically switches to:

- **Model:** `claude-haiku-4-5-20251001`
- **SDK:** `anthropic >= 0.20.0` — uses synchronous `client.messages.create()` and async `AsyncAnthropic` with `messages.stream()`

### Provider Detection Logic

```python
# Automatic provider selection at startup (rag/engine.py):
if GEMINI_API_KEY is set and valid  →  provider = "gemini"
elif ANTHROPIC_API_KEY is set       →  provider = "anthropic"
else                                →  provider = "none"
#  (returns a helpful error message pointing to AI Studio)
```

---

## 🧠 RAG Pipeline — Step-by-Step Data Flow

Every citizen query goes through this pipeline in `rag/engine.py`:

```
┌─────────────────────────────────────────────────┐
│                 CITIZEN QUERY                   │
│     "पीएम किसान में कितना पैसा मिलेगा?"            │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│        1. LANGUAGE DETECTION                    │
│  • Unicode script check (Devanagari/Tamil/etc)  │
│  • Detected: "hi" (Hindi)                       │
│  • Translates query to English for retrieval    │
│    "How much money in PM Kisan"                 │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│        2. TF-IDF RETRIEVAL (RAG)                │
│  • TfidfVectorizer transforms English query     │
│  • cosine_similarity against in-memory matrix   │
│  • Returns top-K chunks (default: 5)            │
│  • Sources: training_data.json + any PDFs       │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│        3. CONTEXT ASSEMBLY                      │
│  • Formats chunks with score labels:            │
│    "[Source: PM-KISAN | Score: 0.87]\n..."      │
│  • Injects into NyayaBot system prompt          │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│        4. LLM GENERATION (Gemini / Claude)      │
│  • System: NyayaBot persona + context + lang    │
│  • Structured output: What is it → Eligibility  │
│    → Benefits (₹6,000/yr) → How to Apply        │
│    → Documents → Helpline (155261)              │
│  • Streaming: word-by-word via async SSE        │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│        5. RESPONSE DELIVERY                     │
│  • ChatResponse with timings (ms): retrieval,   │
│    LLM, input_translation, total                │
│  • Delivered to: Web UI Chat / Telegram Bot     │
└─────────────────────────────────────────────────┘
```

### Chunking Strategy

- **Chunk size:** 512 words with a 64-word overlap (`PolicyDocumentProcessor`)
- **Minimum chunk length:** 20 characters (short fragments are discarded)
- **Chunk ID format:** `{scheme_name}_{index:04d}`
- **Index:** TF-IDF matrix built in-memory at startup; rebuilt every time new documents are added

---

## 📂 Project Directory Structure

```
Policy-Navya-Bot-Project/
│
├── backend/
│   ├── __init__.py
│   └── server.py              # FastAPI app: REST endpoints, SSE stream,
│                              #  Telegram webhook receiver, static file serving
│
├── bot/
│   ├── __init__.py
│   └── telegram_bot.py        # Telegram bot: commands (/start /help /language
│                              #  /schemes /clear), typing heartbeat, PDF ingestion,
│                              #  webhook & standalone polling modes
│
├── rag/
│   ├── __init__.py
│   └── engine.py              # Core engine: PolicyDocumentProcessor,
│                              #  TFIDFVectorStore, EmbeddingEngine (dummy),
│                              #  TranslationEngine, NyayaBotRAGEngine
│                              #  (chat, chat_stream, chat_stream_async)
│
├── frontend/
│   ├── index.html             # Citizen chat UI, hero section, scheme directory,
│   │                          #  suggested queries, PDF upload button
│   ├── dashboard.html         # Admin analytics: metrics, scheme bar charts,
│   │                          #  language distribution, recent queries
│   ├── style.css              # Dark-theme glassmorphism design system,
│   │                          #  ambient orbs, CSS animations, responsive layout
│   └── app.js                 # Client-side: SSE streaming consumer, API calls,
│                              #  marked.js Markdown rendering, state management
│
├── config/
│   └── settings.json          # App defaults: chunk_size=512, overlap=64,
│                              #  top_k=5, supported languages, server port
│
├── data/
│   ├── policies/              # Drop PDF / TXT / MD policy documents here
│   │   └── .gitkeep
│   └── training/
│       └── training_data.json # Pre-compiled structured knowledge base
│                              #  (24 KB, 15+ flagship Indian schemes)
│
├── scripts/
│   ├── __init__.py
│   └── ingest.py              # Standalone batch ingestion: indexes all files
│                              #  in data/policies/ + training data, prints summary
│
├── .env.example               # Template for all required environment variables
├── .gitignore                 # Excludes .env, venv/, __pycache__, uploaded PDFs
├── Procfile                   # Process file: uvicorn backend.server:app
├── render.yaml                # Render.com Blueprint: single web service, envVars,
│                              #  health check path (/api/health)
├── requirements.txt           # 13 pinned Python packages
├── runtime.txt                # Python 3.11 runtime declaration
└── README.md                  # This file
```

---

## 🚀 Installation & Setup Guide

### Prerequisites

- Python **3.11** (as declared in `runtime.txt`)
- A free [Google AI Studio API key](https://aistudio.google.com/apikey)
- (Optional) A Telegram Bot token from [@BotFather](https://t.me/BotFather)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/Policy-Navya-Bot-Project.git
cd Policy-Navya-Bot-Project
```

### 2. Create a Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in your credentials:

```env
GEMINI_API_KEY=AIzaSyYourActualGoogleGeminiKeyHere
TELEGRAM_BOT_TOKEN=7123456789:ABCdefGHI...   # Optional
WEBHOOK_URL=https://your-app.onrender.com     # Optional, for cloud deployment
```

---

## ⚙️ Environment Configuration (.env)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | **Yes (Primary)** | `""` | Google Gemini API Key. [Get free key →](https://aistudio.google.com/apikey) |
| `ANTHROPIC_API_KEY` | Optional | `""` | Anthropic API Key. Used as LLM fallback if no Gemini key is configured. |
| `GEMINI_MODEL` | Optional | `gemini-3.5-flash-lite` | Override the Gemini model (e.g. `gemini-2.0-flash`). |
| `TELEGRAM_BOT_TOKEN` | Optional | `""` | Telegram Bot token from [@BotFather](https://t.me/BotFather). |
| `WEBHOOK_URL` | Optional | `""` | Public HTTPS URL of your deployed server (e.g. `https://my-nyayabot.onrender.com`). Enables automatic Telegram Webhook registration on startup. |
| `PORT` | Optional | `8000` | Port for the FastAPI/uvicorn server. |

### How to Get a Free Google Gemini API Key

1. Go to **[Google AI Studio](https://aistudio.google.com/apikey)**.
2. Sign in with your Google account.
3. Click **"Create API Key"** → select or create a Google Cloud project.
4. Copy the key (starts with `AIzaSy...`) and paste it into `.env`.

### How to Create a Telegram Bot

1. Open Telegram → message **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot` and follow the prompts to choose a name and username.
3. Copy the provided API token and paste it into `.env` as `TELEGRAM_BOT_TOKEN`.

---

## 🖥️ Launching the Application (All Modes)

### Mode 1: Full Unified Application (Recommended)

Starts the FastAPI server, Web UI, and Telegram Webhook on a single process:

```bash
uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload
```

or equivalently:

```bash
python backend/server.py
```

Access in your browser:

| URL | Description |
|---|---|
| `http://localhost:8000` | 🌐 Citizen Chat UI & Scheme Directory |
| `http://localhost:8000/dashboard.html` | 📊 Analytics & System Dashboard |
| `http://localhost:8000/api/docs` | 📖 Interactive Swagger API Docs |
| `http://localhost:8000/api/redoc` | 📖 ReDoc API Documentation |
| `http://localhost:8000/api/health` | ❤️ Health Check (JSON) |

---

### Mode 2: Standalone Telegram Bot (Long Polling)

For local development without a public HTTPS URL or ngrok tunnel:

```bash
python bot/telegram_bot.py
```

> ⚠️ Do not run both Mode 1 (with `WEBHOOK_URL` set) and Mode 2 simultaneously — they will conflict over the Telegram update stream.

---

### Mode 3: Batch Document Ingestion

To index (or re-index) all PDFs, TXT, and Markdown files from `data/policies/`:

```bash
python scripts/ingest.py
```

The script prints a scheme-by-chunk summary on completion. The server also auto-loads `data/training/training_data.json` on every startup.

---

## 📱 Telegram Bot Integration & Commands

When `TELEGRAM_BOT_TOKEN` is configured, the bot operates in Webhook mode on the cloud (via `WEBHOOK_URL`) or Long Polling mode locally.

| Command | Action |
|---|---|
| `/start` | Welcome message + 8-language selection keyboard (English, Hindi, Tamil, Bengali, Telugu, Marathi, Gujarati, Kannada) |
| `/language` | Opens the inline language selection menu to switch response language at any time |
| `/schemes` | Shows inline quick-access buttons: PM-KISAN, PM Awas Yojana, Ayushman Bharat, MGNREGA, Ujjwala Yojana, Jan Dhan |
| `/clear` | Clears in-memory conversation history for the current user session |
| `/help` | Displays all available commands and tips |

### Session Management

- Each user has an in-memory session: `{lang: "en", history: [...]}`
- Conversation history is capped at **20 turns** (oldest entries are dropped)
- The LLM receives the **last 8 turns** of history as context

### Typing Heartbeat

A background `asyncio` task (`_keep_typing`) sends the `"typing"` chat action every 4 seconds while the LLM is processing — so users see the bot is working.

### Uploading PDFs via Telegram

Send any `.pdf` file directly to the bot chat. NyayaBot will:
1. Download the file to a temporary directory.
2. Extract text with PyMuPDF (`fitz`).
3. Chunk and index it into the live TF-IDF store.
4. Confirm: *"✅ Document 'Scheme Name' indexed! Added N knowledge chunks."*

### Response Formatting

Telegram uses a limited Markdown dialect. The `format_for_telegram()` function automatically converts LLM output:
- `## Headers` → `*Bold Headers*`
- `**bold**` → `*bold*`
- `---` horizontal rules → removed
- 3+ consecutive blank lines → collapsed to 2
- Responses over 4,000 characters → truncated with a note

---

## 📡 REST API Reference

Base URL (local): `http://localhost:8000`

---

### `POST /api/chat` — Conversational Chat (Non-Streaming)

**Request body:**
```json
{
  "message": "What is the benefit and eligibility of PM-KISAN?",
  "language": "en",
  "session_id": "citizen_user_123",
  "history": []
}
```

Supported `language` values: `en`, `hi`, `ta`, `bn`, `te`, `mr`, `gu`, `kn`, `ml`, `pa`, `ur`, `or`, `auto`

**Response:**
```json
{
  "answer": "PM-KISAN provides ₹6,000/year in 3 installments of ₹2,000...",
  "language": "en",
  "sources": ["training_data.json"],
  "scheme_names": ["PM-KISAN Samman Nidhi Scheme"],
  "retrieval_time_ms": 11.2,
  "llm_time_ms": 540.8,
  "total_time_ms": 552.0,
  "confidence": 0.87,
  "input_translation_ms": 0.0,
  "output_translation_ms": 0.0,
  "session_id": "citizen_user_123"
}
```

---

### `POST /api/chat/stream` — Word-by-Word Streaming (SSE)

Streams the LLM response token-by-token using Server-Sent Events. Uses `engine.chat_stream_async()` which is a true async generator backed by `client.aio.models.generate_content_stream`. Each SDK chunk is split word-by-word server-side with `await asyncio.sleep(0)` between words to guarantee one SSE frame per word.

**Request body:**
```json
{
  "message": "How to apply for Ayushman Bharat?",
  "language": "en",
  "history": []
}
```

**SSE Frame format (during generation):**
```
data: {"token": "Ayushman ", "done": false}
data: {"token": "Bharat ", "done": false}
...
data: {"token": "", "done": true}
```

**On error:**
```
data: {"error": "...", "done": true}
```

**Response headers:** `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`

---

### `POST /api/upload-policy` — Upload a Policy Document

Method: `multipart/form-data`

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file` | Binary | Yes | `.pdf` or `.txt` file |
| `scheme_name` | String | No | Scheme name (auto-derived from filename if omitted) |

**Response:**
```json
{
  "success": true,
  "chunks_added": 16,
  "scheme_name": "PM Surya Ghar Muft Bijli Yojana"
}
```

---

### `GET /api/schemes` — List All Indexed Schemes

Returns all schemes currently in the TF-IDF index with their chunk counts and source filenames.

---

### `GET /api/search` — Semantic Text Search

```
GET /api/search?q=farmer+subsidy&top_k=5
```

**Response:**
```json
{
  "query": "farmer subsidy",
  "results": [
    {
      "scheme": "PM-KISAN Samman Nidhi Scheme",
      "section": "General",
      "content": "PM-KISAN scheme provides direct income support...",
      "score": 0.412
    }
  ]
}
```

---

### `GET /api/stats` — Knowledge Base Statistics

Returns total chunks, total unique schemes, and chunk distribution per scheme.

---

### `GET /api/health` — Health Check

```json
{
  "status": "ok",
  "engine_loaded": true,
  "chunks_in_index": 128,
  "telegram_bot_loaded": true,
  "telegram_webhook_registered": true,
  "version": "1.0.0"
}
```

---

### `POST /api/telegram-webhook` — Telegram Update Receiver

Receives raw Telegram update JSON via POST from the Telegram servers.
Also available at `/telegram-webhook` (without the `/api` prefix). Both paths route to the same handler.

---

## 📚 Expanding the Knowledge Base

NyayaBot supports three methods for adding new government scheme knowledge:

### Method 1: Drop Files into `data/policies/`

1. Place any `.pdf`, `.txt`, or `.md` policy document into `data/policies/`.
2. Run the batch ingestion script:
   ```bash
   python scripts/ingest.py
   ```
   The script processes all files and prints a per-scheme chunk summary.

### Method 2: Upload via Web UI

1. Open `http://localhost:8000`.
2. Click the 📎 (paperclip) button in the chat input area → select a PDF.
3. The document is uploaded to `POST /api/upload-policy`, chunked, and indexed immediately into the live TF-IDF store.

### Method 3: Upload via Telegram

1. Open the Telegram bot chat.
2. Attach and send a `.pdf` file. NyayaBot parses and indexes it automatically.

> **Important:** The TF-IDF index is **in-memory only**. It is rebuilt each time the server starts from `data/training/training_data.json` and any PDFs currently in `data/policies/`. Files uploaded at runtime (via Web UI or Telegram) are indexed in-memory for the session but not persisted to disk. To keep them permanently, copy the source PDFs to `data/policies/`.

---

## 🌐 Multilingual Support & Indian Languages

NyayaBot natively supports 12 Indian languages:

| Language | Code | Script | Detection Method |
|---|---|---|---|
| **English** | `en` | Latin | Default fallback |
| **Hindi** | `hi` | Devanagari (U+0900–U+097F) | Unicode range check |
| **Tamil** | `ta` | Tamil (U+0B80–U+0BFF) | Unicode range check |
| **Bengali** | `bn` | Bengali (U+0980–U+09FF) | Unicode range check |
| **Telugu** | `te` | Telugu (U+0C00–U+0C7F) | Unicode range check |
| **Marathi** | `mr` | Devanagari | `deep-translator` |
| **Gujarati** | `gu` | Gujarati | `deep-translator` |
| **Kannada** | `kn` | Kannada | `deep-translator` |
| **Malayalam** | `ml` | Malayalam | `deep-translator` |
| **Punjabi** | `pa` | Gurmukhi | `deep-translator` |
| **Urdu** | `ur` | Perso-Arabic | `deep-translator` |
| **Odia** | `or` | Odia | `deep-translator` |

### Translation Pipeline

1. Non-English queries are translated **to English** before TF-IDF retrieval (for accuracy of matching against the English knowledge base).
2. The LLM system prompt instructs Gemini to **respond directly in the target language** — no post-processing of the output is needed.
3. In async streaming mode, input translation is offloaded via `asyncio.to_thread()` to avoid blocking the event loop.
4. Translation results are **cached in-memory** (keyed by `(text, source_lang, target_lang)`) to avoid redundant API calls.

> **Note:** Language detection is script-based for Devanagari, Tamil, Bengali, and Telugu. For other languages, set `language` explicitly in the request (or use `"auto"` for best-effort detection).

---

## ☁️ Production Deployment on Render.com

NyayaBot ships with a ready-to-use `render.yaml` blueprint:

```yaml
services:
  - type: web
    name: nyayabot-web
    env: python
    plan: free
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn backend.server:app --host 0.0.0.0 --port $PORT"
    healthCheckPath: /api/health
    envVars:
      - key: GEMINI_API_KEY
      - key: TELEGRAM_BOT_TOKEN
      - key: WEBHOOK_URL
      - key: GEMINI_MODEL
        value: gemini-3.5-flash-lite
      - key: ANTHROPIC_API_KEY
      - key: PYTHON_VERSION
        value: 3.11.0
```

### Deployment Steps

1. Push your project code to GitHub.
2. Log into the [Render Dashboard](https://dashboard.render.com).
3. Click **New +** → **Blueprint** → connect your GitHub repository.
4. Set the required environment variables in Render's dashboard:
   - `GEMINI_API_KEY` — your Google Gemini API key
   - `TELEGRAM_BOT_TOKEN` — (optional) your Telegram bot token
   - `WEBHOOK_URL` — `https://your-service-name.onrender.com`
5. Click **Apply Blueprint**. Render builds and deploys automatically.

> On startup, the FastAPI `@app.on_event("startup")` handler automatically calls `bot.set_webhook(url=WEBHOOK_URL + "/api/telegram-webhook")` so no manual webhook registration is needed.

---

## ❓ Troubleshooting & FAQ

### Q1: The server shows `[WARNING] No AI API key found in .env!`
**Solution:** Ensure `.env` exists at the project root and contains `GEMINI_API_KEY=AIzaSy...` (no quotes, no spaces around `=`). The server loads `.env` before importing any other module, so the file must be in the project root directory.

### Q2: The Telegram bot is not responding during local testing
**Solution:** Run in standalone Long Polling mode (does not require a public HTTPS URL):
```bash
python bot/telegram_bot.py
```

### Q3: How do I change the Gemini model?
**Solution:** In `.env`, set `GEMINI_MODEL=gemini-2.0-flash`. Supported values include `gemini-3.5-flash-lite` (default, lower latency) and `gemini-2.0-flash` (higher quality, higher latency).

### Q4: Port 8000 is already in use
**Solution:** Start uvicorn on a different port:
```bash
uvicorn backend.server:app --port 8080
```

### Q5: PDF upload returns "Could not process PDF"
**Solution:** NyayaBot requires **text-based PDFs** (not scanned images). The file must contain selectable/searchable text. Scanned image PDFs require an OCR pre-processing step (not included in this project).

### Q6: Answers are in English even when I set `language: "hi"`
**Solution:** Gemini is instructed via system prompt to respond in the target language, but output quality depends on the model. `gemini-2.0-flash` generally produces better multilingual output than `gemini-3.5-flash-lite`. Set `GEMINI_MODEL=gemini-2.0-flash` in `.env` for improved Indic language responses.

### Q7: The knowledge base is empty after restarting the server
**Solution:** The TF-IDF index is in-memory only. It is rebuilt at every startup from `data/training/training_data.json` and any files in `data/policies/`. To persist documents across restarts, copy the source PDFs/TXT files into `data/policies/` before starting the server, or run `python scripts/ingest.py` as a pre-start step.

---

## 📜 License & Data Sources

- **License:** This project is open-source under the [MIT License](LICENSE).
- **Official Data Sources:** Policy data is sourced from official Indian Government portals:
  - [india.gov.in](https://www.india.gov.in) — National Portal of India
  - [pmkisan.gov.in](https://pmkisan.gov.in) — Pradhan Mantri Kisan Samman Nidhi
  - [pmjay.gov.in](https://pmjay.gov.in) — Ayushman Bharat PM-JAY
  - [nrega.nic.in](https://nrega.nic.in) — Mahatma Gandhi NREGA
  - [pmaymis.gov.in](https://pmaymis.gov.in) — PM Awas Yojana (Urban)
  - [pmuy.gov.in](https://pmuy.gov.in) — PM Ujjwala Yojana
  - [pmjdy.gov.in](https://pmjdy.gov.in) — PM Jan Dhan Yojana

---

**NyayaBot is dedicated to making government welfare transparent, accessible, and understandable for every Indian citizen.** 🇮🇳

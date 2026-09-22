"""
NyayaBot RAG Engine - Production Version
Uses TF-IDF + Google Gemini 2.0 Flash - No torch/sentence-transformers needed
"""

import asyncio, os, json, time, logging, re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class PolicyChunk:
    chunk_id: str
    scheme_name: str
    section: str
    content: str
    source_file: str
    page_num: int
    embedding: Optional[np.ndarray] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    chunk: PolicyChunk
    score: float
    rank: int


@dataclass
class ChatResponse:
    answer: str
    language: str
    sources: List[str]
    scheme_names: List[str]
    retrieval_time_ms: float
    llm_time_ms: float
    total_time_ms: float
    confidence: float
    input_translation_ms: float = 0.0
    output_translation_ms: float = 0.0


class PolicyDocumentProcessor:
    def __init__(self, chunk_size=512, overlap=64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process_pdf(self, pdf_path: str, scheme_name: str) -> List[PolicyChunk]:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            full_text = ""
            for page in doc:
                full_text += page.get_text("text") + "\n\n"
            doc.close()
            return self.process_text(full_text, scheme_name, Path(pdf_path).name)
        except Exception as e:
            logger.error(f"PDF error: {e}")
            return []

    def process_text(self, text: str, scheme_name: str, source: str = "manual") -> List[PolicyChunk]:
        chunks = []
        words = text.split()
        chunk_idx = 0
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            if len(chunk_text.strip()) < 20:
                continue
            chunk = PolicyChunk(
                chunk_id=f"{scheme_name}_{chunk_idx:04d}",
                scheme_name=scheme_name,
                section="General",
                content=chunk_text,
                source_file=source,
                page_num=1
            )
            chunks.append(chunk)
            chunk_idx += 1
        return chunks


class TFIDFVectorStore:
    """Simple TF-IDF based vector store - no FAISS needed"""

    def __init__(self, **kwargs):
        self.chunks: List[PolicyChunk] = []
        self.vectorizer = None
        self.matrix = None
        logger.info("Using TF-IDF vector store (no FAISS)")

    def add_chunks(self, chunks: List[PolicyChunk], embedder=None):
        self.chunks.extend(chunks)
        self._rebuild_index()
        logger.info(f"Vector store: {len(self.chunks)} chunks")

    def _rebuild_index(self):
        if not self.chunks:
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words=None
            )
            texts = [c.content for c in self.chunks]
            self.matrix = self.vectorizer.fit_transform(texts)
            logger.info(f"TF-IDF index built: {self.matrix.shape}")
        except Exception as e:
            logger.error(f"Index build error: {e}")

    def search(self, query_embedding, top_k: int = 5) -> List[RetrievalResult]:
        return []

    def search_text(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        if not self.chunks or self.vectorizer is None or self.matrix is None:
            return []
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            q_vec = self.vectorizer.transform([query])
            scores = cosine_similarity(q_vec, self.matrix).flatten()
            top_indices = np.argsort(scores)[::-1][:top_k]
            results = []
            for rank, idx in enumerate(top_indices):
                if scores[idx] > 0:
                    results.append(RetrievalResult(
                        chunk=self.chunks[idx],
                        score=float(scores[idx]),
                        rank=rank + 1
                    ))
            return results
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def save(self):
        pass  # No persistence needed for TF-IDF

    def load(self):
        return False  # Always rebuild


class EmbeddingEngine:
    """Dummy embedding engine - TF-IDF handles everything"""
    def __init__(self, **kwargs):
        self.dimension = 100
        self.model = None
        self.model_name = "tfidf"
        logger.info("Using TF-IDF embeddings (lightweight deployment mode)")

    def embed(self, texts):
        return np.zeros((len(texts), self.dimension))

    def embed_single(self, text):
        return np.zeros(self.dimension)


class TranslationEngine:
    SUPPORTED_LANGS = {
        "en": "English", "hi": "Hindi", "ta": "Tamil", "bn": "Bengali",
        "te": "Telugu", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada",
        "ml": "Malayalam", "pa": "Punjabi", "ur": "Urdu", "or": "Odia"
    }

    def __init__(self):
        self.backend = None
        self._cache: Dict[Tuple[str, str, str], str] = {}
        try:
            from deep_translator import GoogleTranslator
            self.backend = "deep_translator"
            logger.info("Translation: using deep-translator backend with in-memory caching")
        except ImportError:
            logger.warning("Translation disabled")

    def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        if not text or not text.strip():
            return text
        if target_lang == source_lang or (target_lang == "en" and source_lang == "en"):
            return text
        
        cache_key = (text.strip(), source_lang, target_lang)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.backend:
            return text
        try:
            from deep_translator import GoogleTranslator
            res = GoogleTranslator(source=source_lang, target=target_lang).translate(text) or text
            self._cache[cache_key] = res
            return res
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    def detect_language(self, text: str) -> str:
        if not text:
            return "en"
        if any("\u0900" <= c <= "\u097F" for c in text):
            return "hi"
        if any("\u0B80" <= c <= "\u0BFF" for c in text):
            return "ta"
        if any("\u0980" <= c <= "\u09FF" for c in text):
            return "bn"
        if any("\u0C00" <= c <= "\u0C7F" for c in text):
            return "te"
        return "en"


class NyayaBotRAGEngine:
    SYSTEM_PROMPT = """You are NyayaBot, an expert AI assistant helping Indian citizens understand government welfare schemes and policies.

Your role:
- Explain policies in SIMPLE, PLAIN language
- Structure: What is it -> Who is eligible -> Benefits -> How to apply -> Documents -> Helpline
- Be accurate, helpful, and empathetic
- Always include amounts, deadlines, helpline numbers

Retrieved Policy Context:
{context}

Answer in: {language}"""

    # Gemini model — gemini-3.5-flash-lite is optimized for low latency and high throughput
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    def __init__(self, api_key=None, vector_store_path="data/faiss_index", policies_dir="data/policies"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
        self.policies_dir = Path(policies_dir)

        self.processor = PolicyDocumentProcessor()
        self.embedder = EmbeddingEngine()
        self.vector_store = TFIDFVectorStore()
        self.translator = TranslationEngine()

        self.provider = self._detect_provider()
        self.client = self._init_client()

        logger.info("Building knowledge base from training data...")
        self._load_builtin_knowledge()
        self.ingest_all_policies()

    def _detect_provider(self):
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if gemini_key and "your_" not in gemini_key:
            logger.info(f"AI Provider: Google Gemini (Model: {self.GEMINI_MODEL})")
            return "gemini"
        elif anthropic_key and "your_" not in anthropic_key:
            logger.info("AI Provider: Anthropic")
            return "anthropic"
        logger.warning("No AI API key found! Set GEMINI_API_KEY in .env")
        return "none"

    def _init_client(self):
        if self.provider == "gemini" and GEMINI_AVAILABLE:
            return genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        elif self.provider == "anthropic" and ANTHROPIC_AVAILABLE:
            return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        return None

    def ingest_all_policies(self):
        self.policies_dir.mkdir(parents=True, exist_ok=True)
        chunks = []
        for pdf in self.policies_dir.glob("*.pdf"):
            scheme = pdf.stem.replace("_", " ").title()
            chunks.extend(self.processor.process_pdf(str(pdf), scheme))
        for txt in self.policies_dir.glob("*.txt"):
            scheme = txt.stem.replace("_", " ").title()
            text = txt.read_text(encoding="utf-8", errors="ignore")
            chunks.extend(self.processor.process_text(text, scheme, txt.name))
        if chunks:
            self.vector_store.add_chunks(chunks)

    def _load_builtin_knowledge(self):
        training_file = Path("data/training/training_data.json")
        if not training_file.exists():
            training_file = Path(__file__).parent.parent / "data" / "training" / "training_data.json"
        if not training_file.exists():
            logger.warning("No training data found")
            return
        try:
            with open(training_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            chunks = []
            for doc in data.get("policy_documents", []):
                text = f"{doc['title']}\n\n{doc['content']}"
                chunks.extend(self.processor.process_text(text, doc["title"], "training_data.json"))
            if chunks:
                self.vector_store.add_chunks(chunks)
                logger.info(f"Loaded {len(chunks)} chunks from training data")
        except Exception as e:
            logger.error(f"Training data error: {e}")

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        start = time.perf_counter()
        results = self.vector_store.search_text(query, top_k=top_k)
        elapsed = (time.perf_counter() - start) * 1000
        logger.debug(f"Retrieval: {len(results)} chunks in {elapsed:.1f}ms")
        return results

    def chat(self, user_message: str, language: str = "en", conversation_history=None, top_k: int = 5) -> ChatResponse:
        t_start = time.perf_counter()

        if language == "auto":
            language = self.translator.detect_language(user_message)

        # 1. Input Translation (if query is not English)
        t_in_trans = time.perf_counter()
        query_en = user_message
        if language != "en":
            detected_src = self.translator.detect_language(user_message)
            query_en = self.translator.translate(user_message, "en", detected_src)
        in_trans_ms = (time.perf_counter() - t_in_trans) * 1000

        # 2. RAG Retrieval
        t_retrieve = time.perf_counter()
        results = self.retrieve(query_en, top_k=top_k)
        retrieval_ms = (time.perf_counter() - t_retrieve) * 1000

        context = self._build_context(results)
        sources = list(set(r.chunk.source_file for r in results))
        scheme_names = list(set(r.chunk.scheme_name for r in results))

        lang_name = self.translator.SUPPORTED_LANGS.get(language, "English")
        system = self.SYSTEM_PROMPT.format(context=context, language=lang_name)

        messages = []
        if conversation_history:
            for turn in conversation_history[-8:]:
                messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_message})

        # 3. LLM Generation
        t_llm = time.perf_counter()
        answer = self._call_llm(system, messages)
        llm_ms = (time.perf_counter() - t_llm) * 1000
        total_ms = (time.perf_counter() - t_start) * 1000

        logger.info(
            f"[TIMING] Total: {total_ms:.1f}ms | InTrans: {in_trans_ms:.1f}ms | "
            f"Retrieval: {retrieval_ms:.1f}ms | LLM: {llm_ms:.1f}ms | Lang: {language}"
        )

        return ChatResponse(
            answer=answer,
            language=language,
            sources=sources,
            scheme_names=scheme_names,
            retrieval_time_ms=round(retrieval_ms, 1),
            llm_time_ms=round(llm_ms, 1),
            total_time_ms=round(total_ms, 1),
            confidence=max((r.score for r in results), default=0.0),
            input_translation_ms=round(in_trans_ms, 1),
            output_translation_ms=0.0
        )

    def _build_context(self, results: List[RetrievalResult]) -> str:
        if not results:
            return "No specific policy documents found. Answer based on general knowledge of Indian government schemes."
        parts = []
        for r in results:
            c = r.chunk
            parts.append(f"[Source: {c.scheme_name} | Score: {r.score:.2f}]\n{c.content}")
        return "\n\n---\n\n".join(parts)

    def _call_llm(self, system: str, messages: List[Dict]) -> str:
        if not self.client or self.provider == "none":
            return (
                "No AI API key configured! Add GEMINI_API_KEY to your .env file.\n"
                "Get a free key at: https://aistudio.google.com/apikey"
            )
        try:
            if self.provider == "gemini":
                # Build conversation history for google-genai SDK
                history = []
                for msg in messages[:-1]:
                    role = "model" if msg["role"] == "assistant" else "user"
                    history.append(
                        genai_types.Content(
                            role=role,
                            parts=[genai_types.Part(text=msg["content"])]
                        )
                    )

                # Send clean user query — system instruction is already in GenerateContentConfig
                last_user_text = messages[-1]["content"]

                # Tight exponential backoff for transient 503 / 429 errors (0.5s, 1.0s, 2.0s)
                last_exc = None
                for attempt in range(3):
                    try:
                        response = self.client.models.generate_content(
                            model=self.GEMINI_MODEL,
                            contents=history + [
                                genai_types.Content(
                                    role="user",
                                    parts=[genai_types.Part(text=last_user_text)]
                                )
                            ],
                            config=genai_types.GenerateContentConfig(
                                system_instruction=system,
                                max_output_tokens=2048,
                                temperature=0.2,
                            )
                        )
                        return response.text
                    except Exception as exc:
                        err_str = str(exc)
                        if ("503" in err_str or "UNAVAILABLE" in err_str or
                                "429" in err_str or "RESOURCE_EXHAUSTED" in err_str):
                            last_exc = exc
                            wait = 0.5 * (2 ** attempt)  # 0.5s, 1.0s, 2.0s
                            logger.warning(f"Gemini transient error (attempt {attempt+1}/3), retrying in {wait:.1f}s: {exc}")
                            time.sleep(wait)
                        else:
                            raise
                raise last_exc

            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    system=system,
                    messages=messages
                )
                return response.content[0].text

        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"AI error: {str(e)}"

    def add_document(self, text: str, scheme_name: str, source: str = "user_upload") -> int:
        chunks = self.processor.process_text(text, scheme_name, source)
        if chunks:
            self.vector_store.add_chunks(chunks)
        return len(chunks)

    # ===== STREAMING SUPPORT =====

    def _call_llm_stream(self, system: str, messages: List[Dict]):
        """
        Synchronous generator — yields raw LLM text chunks (tokens) as they arrive.
        Supports both Gemini (generate_content_stream) and Anthropic (messages.stream).
        On misconfiguration, yields a single informational error string.
        """
        if not self.client or self.provider == "none":
            yield (
                "No AI API key configured. Please add GEMINI_API_KEY to your .env file.\n"
                "Get a free key at: https://aistudio.google.com/apikey"
            )
            return

        try:
            if self.provider == "gemini":
                # Reconstruct multi-turn conversation history for the SDK
                history = []
                for msg in messages[:-1]:
                    role = "model" if msg["role"] == "assistant" else "user"
                    history.append(
                        genai_types.Content(
                            role=role,
                            parts=[genai_types.Part(text=msg["content"])]
                        )
                    )

                last_user_text = messages[-1]["content"]
                contents = history + [
                    genai_types.Content(
                        role="user",
                        parts=[genai_types.Part(text=last_user_text)]
                    )
                ]
                gen_config = genai_types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=2048,
                    temperature=0.2,
                )

                response_iter = self.client.models.generate_content_stream(
                    model=self.GEMINI_MODEL,
                    contents=contents,
                    config=gen_config,
                )
                for chunk in response_iter:
                    # chunk.text is None when the chunk carries only metadata
                    if chunk.text:
                        yield chunk.text

            elif self.provider == "anthropic":
                with self.client.messages.stream(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    system=system,
                    messages=messages,
                ) as stream:
                    for text_chunk in stream.text_stream:
                        if text_chunk:
                            yield text_chunk

        except Exception as exc:
            logger.error(f"LLM stream error: {exc}", exc_info=True)
            yield f"\n\n*Error generating response: {exc}*"

    def chat_stream(self, user_message: str, language: str = "en",
                    conversation_history=None, top_k: int = 5):
        """
        Public streaming interface — mirrors chat() but yields LLM token chunks
        instead of returning a completed ChatResponse.

        Pipeline:
          1. Language detection / normalisation
          2. Input translation to English (for retrieval accuracy)
          3. TF-IDF retrieval
          4. Context building and prompt assembly
          5. LLM token stream via _call_llm_stream()

        Yields:
            str: successive text chunks from the LLM.
        """
        if language == "auto":
            language = self.translator.detect_language(user_message)

        # 1. Translate non-English input to English for retrieval
        query_en = user_message
        if language != "en":
            detected_src = self.translator.detect_language(user_message)
            query_en = self.translator.translate(user_message, "en", detected_src)

        # 2. RAG retrieval
        results = self.retrieve(query_en, top_k=top_k)
        context = self._build_context(results)

        # 3. Assemble system prompt with retrieved context and target language
        lang_name = self.translator.SUPPORTED_LANGS.get(language, "English")
        system = self.SYSTEM_PROMPT.format(context=context, language=lang_name)

        # 4. Build message list (last 8 turns of history + new user message)
        messages: List[Dict] = []
        if conversation_history:
            for turn in conversation_history[-8:]:
                messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_message})

        # 5. Stream LLM tokens back to the caller
        logger.info(
            f"[STREAM] Starting | lang={language} | chunks={len(results)} | provider={self.provider}"
        )
        yield from self._call_llm_stream(system, messages)

    # ===== ASYNC STREAMING SUPPORT =====

    async def _call_llm_stream_async(self, system: str, messages: List[Dict]):
        """
        True async generator — yields one word at a time using the LLM provider's
        native async streaming API.

        Gemini path  : client.aio.models.generate_content_stream() — native async.
        Anthropic path: anthropic.AsyncAnthropic with async context manager.

        Each SDK chunk (which may contain multiple words) is split on whitespace
        and yielded word-by-word.  An `await asyncio.sleep(0)` between each word
        hands control back to the asyncio event loop so FastAPI can flush the SSE
        frame immediately — guaranteeing one network frame per word.
        """
        if not self.client or self.provider == "none":
            yield (
                "No AI API key configured. Please add GEMINI_API_KEY to your .env file.\n"
                "Get a free key at: https://aistudio.google.com/apikey"
            )
            return

        try:
            if self.provider == "gemini":
                # Build multi-turn history
                history = []
                for msg in messages[:-1]:
                    role = "model" if msg["role"] == "assistant" else "user"
                    history.append(
                        genai_types.Content(
                            role=role,
                            parts=[genai_types.Part(text=msg["content"])]
                        )
                    )

                last_user_text = messages[-1]["content"]
                contents = history + [
                    genai_types.Content(
                        role="user",
                        parts=[genai_types.Part(text=last_user_text)]
                    )
                ]
                gen_config = genai_types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=2048,
                    temperature=0.2,
                )

                # client.aio is the native async namespace of the google-genai SDK.
                # generate_content_stream() is a coroutine that resolves to an async
                # iterable \u2014 it must be awaited first, then the result iterated.
                stream = await self.client.aio.models.generate_content_stream(
                    model=self.GEMINI_MODEL,
                    contents=contents,
                    config=gen_config,
                )
                async for chunk in stream:
                    if not chunk.text:
                        continue
                    # Split the SDK chunk into individual words and yield each
                    # separately so the browser receives one SSE frame per word.
                    parts = chunk.text.split(" ")
                    for i, part in enumerate(parts):
                        # Re-attach the space that was used as delimiter,
                        # except on the very last part of the chunk (the LLM
                        # will include any trailing whitespace in the next chunk).
                        token = part + (" " if i < len(parts) - 1 else "")
                        if token:  # skip empty strings from consecutive spaces
                            yield token
                            # Yield control to the event loop so the SSE frame
                            # is flushed to the network before the next word.
                            await asyncio.sleep(0)

            elif self.provider == "anthropic" and ANTHROPIC_AVAILABLE:
                async_client = anthropic.AsyncAnthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY", "")
                )
                async with async_client.messages.stream(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    system=system,
                    messages=messages,
                ) as stream:
                    async for text_chunk in stream.text_stream:
                        if not text_chunk:
                            continue
                        parts = text_chunk.split(" ")
                        for i, part in enumerate(parts):
                            token = part + (" " if i < len(parts) - 1 else "")
                            if token:
                                yield token
                                await asyncio.sleep(0)

        except Exception as exc:
            logger.error(f"LLM async stream error: {exc}", exc_info=True)
            yield f"\n\n*Error generating response: {exc}*"

    async def chat_stream_async(self, user_message: str, language: str = "en",
                                conversation_history=None, top_k: int = 5):
        """
        Async public streaming interface — mirrors chat_stream() but uses a true
        async generator so FastAPI never needs to bridge a sync generator.

        Pipeline:
          1. Language detection / normalisation
          2. Input translation to English (blocking IO run in a thread)
          3. TF-IDF retrieval (CPU-bound, fast — runs inline)
          4. Context building and prompt assembly
          5. Token stream via _call_llm_stream_async()

        Yields:
            str: successive word-level text tokens from the LLM.
        """
        if language == "auto":
            language = self.translator.detect_language(user_message)

        # 1. Translate non-English query to English for retrieval accuracy.
        #    deep_translator makes a blocking HTTP call, so offload to a thread
        #    to avoid blocking the asyncio event loop.
        query_en = user_message
        if language != "en":
            detected_src = self.translator.detect_language(user_message)
            query_en = await asyncio.to_thread(
                self.translator.translate, user_message, "en", detected_src
            )

        # 2. TF-IDF retrieval (pure numpy — fast, safe to run inline)
        results = self.retrieve(query_en, top_k=top_k)
        context = self._build_context(results)

        # 3. Assemble system prompt
        lang_name = self.translator.SUPPORTED_LANGS.get(language, "English")
        system = self.SYSTEM_PROMPT.format(context=context, language=lang_name)

        # 4. Build message list (cap at last 8 turns to stay within context limit)
        messages: List[Dict] = []
        if conversation_history:
            for turn in conversation_history[-8:]:
                messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_message})

        logger.info(
            f"[STREAM-ASYNC] Starting | lang={language} | chunks={len(results)} | provider={self.provider}"
        )

        # 5. Stream word-level tokens from the LLM
        async for token in self._call_llm_stream_async(system, messages):
            yield token


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = NyayaBotRAGEngine()
    print("NyayaBot ready!")
    r = engine.chat("What is PM-KISAN?", language="en")
    print("Answer:", r.answer[:200])

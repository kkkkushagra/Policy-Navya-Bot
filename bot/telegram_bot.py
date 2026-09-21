"""
NyayaBot Telegram Bot
Handles policy Q&A for Indian citizens via Telegram.
Supports both Webhook mode (embedded in FastAPI) and Long Polling mode (local standalone).
"""

import os
import sys
import re
import logging
import asyncio
from pathlib import Path
from typing import Dict, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(BASE_DIR)

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from rag.engine import NyayaBotRAGEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances for standalone execution
_global_engine: Optional[NyayaBotRAGEngine] = None
user_sessions: Dict[int, Dict] = {}  # user_id -> {lang, history}


def get_engine() -> NyayaBotRAGEngine:
    global _global_engine
    if _global_engine is None:
        _global_engine = NyayaBotRAGEngine(
            api_key=os.getenv("GEMINI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        )
    return _global_engine


# ===== TELEGRAM FORMATTING HELPER =====
def format_for_telegram(text: str) -> str:
    """
    Convert LLM-generated Markdown to Telegram-compatible Markdown.
    Removes '#' header markers, converts **bold** to *bold*, and strips '---' lines.
    """
    # Step 1: Convert Markdown headers (# / ## / ### ...) -> *Heading text*
    text = re.sub(
        r'^#{1,6}\s*(.+)$',
        lambda m: f'*{m.group(1).strip()}*',
        text,
        flags=re.MULTILINE
    )

    # Step 2: Convert **double-star bold** -> *single-star bold*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)

    # Step 3: Strip bare horizontal rule lines (--- / *** / ___)
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # Step 4: Collapse 3+ consecutive blank lines -> 2 blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ===== LANGUAGE SELECTION KEYBOARD =====
LANG_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
     InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang_hi")],
    [InlineKeyboardButton("தமிழ்", callback_data="lang_ta"),
     InlineKeyboardButton("বাংলা", callback_data="lang_bn")],
    [InlineKeyboardButton("తెలుగు", callback_data="lang_te"),
     InlineKeyboardButton("मराठी", callback_data="lang_mr")],
    [InlineKeyboardButton("ગુજરાતી", callback_data="lang_gu"),
     InlineKeyboardButton("ಕನ್ನಡ", callback_data="lang_kn")]
])

WELCOME_MSG = """🏛 *Welcome to NyayaBot!*

I help Indian citizens understand government schemes and welfare policies.

Ask me about:
• Eligibility for welfare schemes
• Benefits and amounts
• How to apply
• Required documents

Type /language to change language.
Type /schemes to see popular schemes.
Type /help for more commands.

_What would you like to know?_"""


# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    user_sessions[user_id] = {"lang": "en", "history": []}
    if update.message:
        await update.message.reply_text(
            WELCOME_MSG, parse_mode="Markdown",
            reply_markup=LANG_KEYBOARD
        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "🤖 *NyayaBot Commands*\n\n"
            "/start — Restart the bot\n"
            "/language — Change response language\n"
            "/schemes — Browse popular schemes\n"
            "/clear — Clear conversation history\n"
            "/help — Show this help message\n\n"
            "Simply type your question to get started!",
            parse_mode="Markdown"
        )


async def language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "🌐 Choose your preferred language:",
            reply_markup=LANG_KEYBOARD
        )


async def schemes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schemes_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌾 PM-KISAN", callback_data="scheme_PM-KISAN"),
         InlineKeyboardButton("🏠 PM Awas", callback_data="scheme_PM Awas Yojana")],
        [InlineKeyboardButton("🏥 Ayushman", callback_data="scheme_Ayushman Bharat"),
         InlineKeyboardButton("👷 MGNREGA", callback_data="scheme_MGNREGA")],
        [InlineKeyboardButton("🔥 Ujjwala", callback_data="scheme_Ujjwala Yojana"),
         InlineKeyboardButton("🏦 Jan Dhan", callback_data="scheme_Jan Dhan")],
    ])
    if update.message:
        await update.message.reply_text(
            "📋 *Popular Government Schemes*\nTap to learn more:",
            parse_mode="Markdown",
            reply_markup=schemes_keyboard
        )


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user:
        user_id = update.effective_user.id
        if user_id in user_sessions:
            user_sessions[user_id]["history"] = []
    if update.message:
        await update.message.reply_text("✅ Conversation cleared! Ask me anything.")


async def _keep_typing(bot, chat_id: int, stop_event: asyncio.Event):
    """Background task to refresh Telegram typing action every 4s while LLM processes."""
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            pass


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.from_user or not query.data:
        return
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("lang_"):
        lang = query.data[5:]
        if user_id not in user_sessions:
            user_sessions[user_id] = {"lang": lang, "history": []}
        else:
            user_sessions[user_id]["lang"] = lang
        lang_names = {"en": "English", "hi": "हिंदी", "ta": "தமிழ்", "bn": "বাংলা",
                      "te": "తెలుగు", "mr": "मराठी", "gu": "ગુજરાતી", "kn": "ಕನ್ನಡ"}
        await query.edit_message_text(f"✅ Language set to {lang_names.get(lang, lang)}!\n\nNow ask me your question.")

    elif query.data.startswith("scheme_"):
        scheme = query.data[7:]
        await query.edit_message_text(f"⏳ Looking up {scheme}...")
        session = user_sessions.get(user_id, {"lang": "en", "history": []})

        chat_id = query.message.chat_id if query.message else user_id
        stop_typing = asyncio.Event()
        typing_task = asyncio.create_task(
            _keep_typing(context.bot, chat_id, stop_typing)
        )

        eng = context.bot_data.get("rag_engine") or get_engine()
        try:
            t0 = asyncio.get_event_loop().time()
            response = await asyncio.to_thread(
                eng.chat,
                f"Tell me about {scheme} - eligibility, benefits, and how to apply",
                language=session["lang"],
                conversation_history=session["history"]
            )
            t_engine = asyncio.get_event_loop().time()
            formatted_answer = format_for_telegram(response.answer)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📋 *{scheme}*\n\n{formatted_answer}",
                parse_mode="Markdown"
            )
            t_send = asyncio.get_event_loop().time()
            logger.info(
                f"[TELEGRAM SCHEME] Scheme: {scheme} | Engine: {(t_engine - t0)*1000:.0f}ms "
                f"(Retrieval: {response.retrieval_time_ms}ms, LLM: {response.llm_time_ms}ms) | "
                f"Send: {(t_send - t_engine)*1000:.0f}ms | Total: {(t_send - t0)*1000:.0f}ms"
            )
        finally:
            stop_typing.set()
            await typing_task


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_user:
        return

    t_recv = asyncio.get_event_loop().time()
    user_id = update.effective_user.id
    user_text = update.message.text
    chat_id = update.effective_chat.id

    if user_id not in user_sessions:
        user_sessions[user_id] = {"lang": "en", "history": []}

    session = user_sessions[user_id]

    # Start background typing heartbeat
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(_keep_typing(context.bot, chat_id, stop_typing))

    session["history"].append({"role": "user", "content": user_text})

    eng = context.bot_data.get("rag_engine") or get_engine()
    try:
        t_engine_start = asyncio.get_event_loop().time()
        response = await asyncio.to_thread(
            eng.chat,
            user_message=user_text,
            language=session["lang"],
            conversation_history=session["history"]
        )
        t_engine_done = asyncio.get_event_loop().time()

        session["history"].append({"role": "assistant", "content": response.answer})
        if len(session["history"]) > 20:
            session["history"] = session["history"][-20:]

        answer = format_for_telegram(response.answer)
        if len(answer) > 4000:
            answer = answer[:3900] + "\n\n_[Response truncated — ask for more details]_"

        footer = ""
        if response.scheme_names:
            footer = f"\n\n📌 _{', '.join(response.scheme_names[:3])}_"
        if response.retrieval_time_ms:
            footer += f"\n⚡ _{response.total_time_ms:.0f}ms_"

        t_send_start = asyncio.get_event_loop().time()
        await update.message.reply_text(
            answer + footer,
            parse_mode="Markdown"
        )
        t_send_done = asyncio.get_event_loop().time()

        total_wall_ms = (t_send_done - t_recv) * 1000
        send_ms = (t_send_done - t_send_start) * 1000
        in_trans_ms = getattr(response, "input_translation_ms", 0.0)

        logger.info(
            f"[TELEGRAM TIMING] Total: {total_wall_ms:.0f}ms | InTrans: {in_trans_ms:.1f}ms | "
            f"Retrieval: {response.retrieval_time_ms:.1f}ms | LLM: {response.llm_time_ms:.1f}ms | "
            f"Send: {send_ms:.0f}ms | Lang: {session['lang']}"
        )
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await update.message.reply_text("Sorry, an error occurred while processing your request. Please try again.")
    finally:
        stop_typing.set()
        await typing_task


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF uploads via Telegram"""
    if not update.message or not update.message.document:
        return
    doc = update.message.document
    if not (doc.file_name and doc.file_name.endswith('.pdf')):
        await update.message.reply_text("Please send a PDF file.")
        return

    await update.message.reply_text("📄 Processing your PDF...")
    file = await context.bot.get_file(doc.file_id)
    
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        await file.download_to_memory(tmp)
        tmp_path = tmp.name

    scheme_name = Path(doc.file_name).stem.replace('_', ' ').title()
    eng = context.bot_data.get("rag_engine") or get_engine()
    chunks = eng.processor.process_pdf(tmp_path, scheme_name)
    
    if chunks:
        eng.vector_store.add_chunks(chunks, eng.embedder)
        eng.vector_store.save()
        await update.message.reply_text(
            f"✅ Document '{scheme_name}' indexed successfully!\n"
            f"Added {len(chunks)} knowledge chunks.\n\n"
            f"You can now ask questions about this document."
        )
    else:
        await update.message.reply_text("❌ Could not process PDF. Please try a text-based PDF.")
    
    Path(tmp_path).unlink(missing_ok=True)


# ===== APPLICATION FACTORY & WEBHOOK UTILS =====
def build_telegram_app(token: str, rag_engine: Optional[NyayaBotRAGEngine] = None) -> Application:
    """
    Build and configure a python-telegram-bot Application instance for webhook or polling usage.
    """
    app = Application.builder().token(token).updater(None).build()
    
    if rag_engine:
        app.bot_data["rag_engine"] = rag_engine
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("language", language_cmd))
    app.add_handler(CommandHandler("schemes", schemes_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app


async def process_telegram_update(telegram_app: Application, update_dict: dict):
    """Deserialize and dispatch a Telegram update dictionary received via webhook."""
    update = Update.de_json(data=update_dict, bot=telegram_app.bot)
    await telegram_app.process_update(update)


# ===== MAIN (Standalone Long Polling Mode for Local Dev) =====
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "your_telegram_bot_token_here":
        logger.error("TELEGRAM_BOT_TOKEN not set in environment or .env!")
        return

    logger.info("Starting NyayaBot Telegram bot in standalone polling mode...")
    # For local standalone polling, instantiate with default updater
    app = Application.builder().token(token).build()
    app.bot_data["rag_engine"] = get_engine()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("language", language_cmd))
    app.add_handler(CommandHandler("schemes", schemes_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

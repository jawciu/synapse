import os
import logging
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from telegram import Update
from telegram.error import Conflict
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from .agent import _init, build_reflection_graph, get_conn_and_vector_store
from .auth import (
    get_user_by_telegram_id,
    link_telegram_to_user,
    login_user,
    register_user_from_telegram,
)
from .chat_agent import build_chat_agent
from .db import get_connection
from .graph_store import make_graph_tools
from .service import run_reflection_pipeline, run_chat

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Initialize shared resources once ──
_init()
reflection_graph = build_reflection_graph()
_conn = get_connection()

# ── Per-user state ──
# Tracks users in the middle of /reflect or registration/link flows
_pending_reflect: set[int] = set()
_stopping_for_conflict = False

# Registration flow states: {telegram_id: {"step": "email"|"password", "email": str}}
_reg_flow: dict[int, dict] = {}

# Link flow states: {telegram_id: {"step": "email"|"password", "email": str}}
_link_flow: dict[int, dict] = {}


# ── Helpers ──

def _get_user_id(telegram_id: int) -> str | None:
    return get_user_by_telegram_id(_conn, telegram_id)


def _build_chat_agent_for(user_id: str):
    conn, vector_store = get_conn_and_vector_store()
    _, chat_tools = make_graph_tools(conn, vector_store, user_id=user_id)
    return build_chat_agent(chat_tools)


async def _require_auth(update: Update) -> str | None:
    """Return user_id if authenticated, else prompt registration and return None."""
    user_id = _get_user_id(update.effective_user.id)
    if user_id:
        return user_id
    await update.message.reply_text(
        "Welcome to *synapse*.\n\n"
        "You don't have an account yet. Send me your *email address* to create one, "
        "or use /link if you already have a web account.",
        parse_mode="Markdown",
    )
    _reg_flow[update.effective_user.id] = {"step": "email"}
    return None


# ── Command handlers ──

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _get_user_id(update.effective_user.id)
    if user_id:
        await update.message.reply_text(
            "Welcome back to *synapse*.\n\n"
            "Send me a voice note or text to reflect, or ask me anything about your patterns.\n\n"
            "• /reflect — submit a journal entry\n"
            "• /cancel — go back to chat mode\n"
            "• /link — link this Telegram to a different account",
            parse_mode="Markdown",
        )
        await register_nudge(update, context)
    else:
        await update.message.reply_text(
            "Welcome to *synapse* — your personal reflection coach.\n\n"
            "Let's get you set up. Send me your *email address* to create an account, "
            "or use /link if you already have a web account.",
            parse_mode="Markdown",
        )
        _reg_flow[update.effective_user.id] = {"step": "email"}


async def reflect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = await _require_auth(update)
    if not user_id:
        return
    _pending_reflect.add(update.effective_user.id)
    await update.message.reply_text(
        "What's on your mind? Send me your reflection and I'll analyze it and save it to your graph.\n\n"
        "_Send /cancel to go back to chat mode._",
        parse_mode="Markdown",
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tid = update.effective_user.id
    _pending_reflect.discard(tid)
    _reg_flow.pop(tid, None)
    _link_flow.pop(tid, None)
    await update.message.reply_text("Cancelled. Send me anything to chat about your patterns.")


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Link this Telegram account to an existing web account."""
    tid = update.effective_user.id
    _pending_reflect.discard(tid)
    _reg_flow.pop(tid, None)
    _link_flow[tid] = {"step": "email"}
    await update.message.reply_text(
        "Send me the *email* for your existing synapse web account.",
        parse_mode="Markdown",
    )


# ── Registration flow handler ──

async def _handle_registration(update: Update, text: str) -> bool:
    """Handle multi-step registration. Returns True if we consumed the message."""
    tid = update.effective_user.id
    state = _reg_flow.get(tid)
    if not state:
        return False

    if state["step"] == "email":
        _reg_flow[tid] = {"step": "password", "email": text.strip()}
        await update.message.reply_text(
            "Got it. Now send me a *password* (at least 6 characters).",
            parse_mode="Markdown",
        )
        return True

    if state["step"] == "password":
        email = state["email"]
        password = text.strip()
        _reg_flow.pop(tid, None)
        try:
            result = register_user_from_telegram(_conn, email, password, tid)
            await update.message.reply_text(
                f"Account created for *{result['email']}*.\n\n"
                "You're all set! Send me a voice note or text to start reflecting.",
                parse_mode="Markdown",
            )
        except Exception as exc:
            await update.message.reply_text(
                f"Sorry, I couldn't create your account: {exc}\n\n"
                "Try again with a different email, or use /link if you have an existing account."
            )
        return True

    return False


# ── Link flow handler ──

async def _handle_link(update: Update, text: str) -> bool:
    """Handle multi-step account linking. Returns True if we consumed the message."""
    tid = update.effective_user.id
    state = _link_flow.get(tid)
    if not state:
        return False

    if state["step"] == "email":
        _link_flow[tid] = {"step": "password", "email": text.strip()}
        await update.message.reply_text("Now send your *password*.", parse_mode="Markdown")
        return True

    if state["step"] == "password":
        email = state["email"]
        password = text.strip()
        _link_flow.pop(tid, None)
        try:
            result = login_user(_conn, email, password)
            link_telegram_to_user(_conn, result["user_id"], tid)
            _reg_flow.pop(tid, None)
            await update.message.reply_text(
                f"Linked! Your Telegram is now connected to *{result['email']}*.\n\n"
                "Send a voice note or text anytime and I'll save it to your graph.",
                parse_mode="Markdown",
            )
        except Exception as exc:
            await update.message.reply_text(f"Couldn't link: {exc}. Try /link again.")
        return True

    return False


# ── Main text message handler ──

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tid = update.effective_user.id
    text = update.message.text

    # Link flow takes precedence so /link can't be hijacked by stale registration state.
    if await _handle_link(update, text):
        return
    if await _handle_registration(update, text):
        return

    user_id = await _require_auth(update)
    if not user_id:
        return

    await update.message.chat.send_action("typing")

    # Reflect mode
    if tid in _pending_reflect:
        _pending_reflect.discard(tid)
        await update.message.reply_text("Analyzing your reflection... this takes 20-30 seconds.")
        await update.message.chat.send_action("typing")

        count = context.user_data.get("reflection_count", 0) + 1
        context.user_data["reflection_count"] = count
        config_thread = f"tg-reflect-{tid}-{count}"

        result = reflection_graph.invoke(
            {"reflection_text": text, "daily_prompt": None, "source": "telegram_text", "user_id": user_id, "messages": []},
            config={"configurable": {"thread_id": config_thread}},
        )
        await _send_reflection_result(update, result, text)
        return

    # Chat mode
    raw = run_chat(message=text, thread_id=f"tg-{tid}", user_id=user_id)
    messages = raw.get("messages", [])
    answer = next((m["content"] for m in reversed(messages) if m.get("role") in ("ai", "assistant")), "")
    await update.message.reply_text(answer or "I couldn't find an answer.")


# ── Voice handler ──

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tid = update.effective_user.id

    user_id = await _require_auth(update)
    if not user_id:
        return

    await update.message.chat.send_action("typing")
    await update.message.reply_text("Got your voice note! Transcribing...")

    voice_file = await update.message.voice.get_file()

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        await voice_file.download_to_drive(tmp_path)
        openai_client = OpenAI()
        with open(tmp_path, "rb") as audio:
            transcription = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
            )
        text = transcription.text
        logger.info("Voice transcription for user %s: %s", tid, text)
    finally:
        os.remove(tmp_path)

    await update.message.reply_text("Analyzing your voice note... this takes 20-30 seconds.")
    await update.message.chat.send_action("typing")

    count = context.user_data.get("reflection_count", 0) + 1
    context.user_data["reflection_count"] = count

    result = reflection_graph.invoke(
        {"reflection_text": text, "daily_prompt": None, "source": "voice", "user_id": user_id, "messages": []},
        config={"configurable": {"thread_id": f"tg-reflect-{tid}-{count}"}},
    )
    await _send_reflection_result(update, result, text)


async def _send_reflection_result(update: Update, result: dict, original_text: str) -> None:
    extracted = result.get("extracted", {})
    patterns = [p["name"] for p in extracted.get("patterns", [])]
    emotions = [e["name"] for e in extracted.get("emotions", [])]
    insights = result.get("insights", "")
    questions = result.get("follow_up_questions", [])

    snippet = original_text[:120] + ("..." if len(original_text) > 120 else "")
    response = f"_\"{snippet}\"_\n\n"
    if patterns:
        response += f"*Patterns:* {', '.join(patterns)}\n"
    if emotions:
        response += f"*Emotions:* {', '.join(emotions)}\n"
    if insights:
        response += f"\n*Insights:*\n{insights}\n"
    if questions:
        response += "\n*Reflect on:*\n" + "\n".join(f"• {q}" for q in questions)

    await update.message.reply_text(response or "Reflection saved!", parse_mode="Markdown")


# ── Nudge job ──

async def daily_nudge(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id
    tid = context.job.data.get("telegram_id")
    user_id = get_user_by_telegram_id(_conn, tid) if tid else None

    if not user_id:
        return

    ifs_parts = _conn.query(
        "SELECT name, role, description FROM ifs_part WHERE user_id = $user_id ORDER BY occurrences DESC LIMIT 1",
        {"user_id": user_id},
    )
    schemas = _conn.query(
        "SELECT name, domain, description FROM schema_pattern WHERE user_id = $user_id ORDER BY occurrences DESC LIMIT 1",
        {"user_id": user_id},
    )

    if not ifs_parts and not schemas:
        return

    if ifs_parts and not isinstance(ifs_parts, str):
        subject = f"IFS part: '{ifs_parts[0]['name']}' ({ifs_parts[0]['role']}) — {ifs_parts[0]['description']}"
    elif schemas and not isinstance(schemas, str):
        subject = f"schema: '{schemas[0]['name']}' ({schemas[0]['domain']}) — {schemas[0]['description']}"
    else:
        return

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)
    prompt = (
        f"You are a compassionate reflection coach. "
        f"Write a single short, warm nudge message (2-3 sentences max) for someone whose most active {subject}. "
        f"Be gentle, curious, and normalizing. Don't be clinical. End with a brief open question."
    )
    response = llm.invoke(prompt)
    await context.bot.send_message(chat_id=chat_id, text=response.content)


async def register_nudge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    tid = update.effective_user.id
    for job in context.job_queue.get_jobs_by_name(f"nudge-{chat_id}"):
        job.schedule_removal()
    context.job_queue.run_repeating(
        daily_nudge,
        interval=6 * 3600,
        first=10,
        chat_id=chat_id,
        name=f"nudge-{chat_id}",
        data={"telegram_id": tid},
    )


# ── Error handler ──

async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    global _stopping_for_conflict
    if isinstance(context.error, Conflict):
        if _stopping_for_conflict:
            return
        _stopping_for_conflict = True
        logger.error("Telegram polling conflict — stopping this process.")
        context.application.stop_running()
        return
    logger.exception("Unhandled Telegram bot error", exc_info=context.error)


# ── Entry point ──

def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reflect", reflect_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_error_handler(handle_error)

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

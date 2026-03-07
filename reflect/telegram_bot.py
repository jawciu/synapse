import os
import logging
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from .chat_agent import build_chat_agent
from .agent import _init, build_reflection_graph
from .db import get_connection

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Initialize shared resources once ──
_init()
chat_agent = build_chat_agent()
reflection_graph = build_reflection_graph()
_conn = get_connection()

# Track users waiting to submit a reflection
_pending_reflect: set[int] = set()


# ── Handlers ──

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to *ReflectGraph* 🌱\n\n"
        "I'm your personal reflection coach. I track your emotional patterns over time using a knowledge graph.\n\n"
        "Just send me anything that's on your mind and I'll help you understand your patterns.\n\n"
        "*Commands:*\n"
        "• /reflect — submit a journal entry to analyze & save to your graph\n"
        "• /cancel — go back to chat mode\n\n"
        "*Or just ask me anything:*\n"
        "• _What patterns do I repeat most?_\n"
        "• _Why do I always feel anxious?_\n"
        "• _What does my inner critic do?_",
        parse_mode="Markdown",
    )


async def reflect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask the user to send their reflection text."""
    user_id = update.effective_user.id
    _pending_reflect.add(user_id)
    await update.message.reply_text(
        "What's on your mind? Send me your reflection and I'll analyze it, extract patterns, and save it to your graph.\n\n"
        "_Send /cancel to go back to chat mode._",
        parse_mode="Markdown",
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    _pending_reflect.discard(user_id)
    await update.message.reply_text("Cancelled. Back to chat mode — ask me anything about your patterns.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text

    await update.message.chat.send_action("typing")

    # If user is in reflect mode, run the full pipeline
    if user_id in _pending_reflect:
        _pending_reflect.discard(user_id)
        await update.message.reply_text("Analyzing your reflection... this takes 20-30 seconds.")
        await update.message.chat.send_action("typing")

        count = context.user_data.get("reflection_count", 0) + 1
        context.user_data["reflection_count"] = count
        config = {"configurable": {"thread_id": f"tg-reflect-{user_id}-{count}"}}

        result = reflection_graph.invoke(
            {"reflection_text": text, "daily_prompt": None, "source": "telegram_text", "messages": []},
            config=config,
        )

        extracted = result.get("extracted", {})
        patterns = [p["name"] for p in extracted.get("patterns", [])]
        emotions = [e["name"] for e in extracted.get("emotions", [])]
        insights = result.get("insights", "")
        questions = result.get("follow_up_questions", [])

        response = ""
        if patterns:
            response += f"*Patterns:* {', '.join(patterns)}\n"
        if emotions:
            response += f"*Emotions:* {', '.join(emotions)}\n"
        if insights:
            response += f"\n*Insights:*\n{insights}\n"
        if questions:
            response += "\n*Reflect on:*\n" + "\n".join(f"• {q}" for q in questions)

        await update.message.reply_text(response or "Reflection saved!", parse_mode="Markdown")
        return

    # Otherwise: chat mode
    config = {"configurable": {"thread_id": f"tg-{user_id}"}}
    result = chat_agent.invoke(
        {"messages": [HumanMessage(content=text)]},
        config=config,
    )
    answer = result["messages"][-1].content
    await update.message.reply_text(answer)


# ── Voice handler ──

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
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
        logger.info("Voice transcription for user %s: %s", user_id, text)
    finally:
        os.remove(tmp_path)

    await update.message.reply_text("Analyzing your voice note... this takes 20-30 seconds.")
    await update.message.chat.send_action("typing")

    count = context.user_data.get("reflection_count", 0) + 1
    context.user_data["reflection_count"] = count
    config = {"configurable": {"thread_id": f"tg-reflect-{user_id}-{count}"}}

    result = reflection_graph.invoke(
        {"reflection_text": text, "daily_prompt": None, "source": "voice", "messages": []},
        config=config,
    )

    extracted = result.get("extracted", {})
    patterns = [p["name"] for p in extracted.get("patterns", [])]
    emotions = [e["name"] for e in extracted.get("emotions", [])]
    insights = result.get("insights", "")
    questions = result.get("follow_up_questions", [])

    snippet = text[:120] + ("..." if len(text) > 120 else "")
    response = f"I've transcribed your voice note and added it to your graph. Here is what I heard: _{snippet}_\n\n"
    if patterns:
        response += f"*Patterns:* {', '.join(patterns)}\n"
    if emotions:
        response += f"*Emotions:* {', '.join(emotions)}\n"
    if insights:
        response += f"\n*Insights:*\n{insights}\n"
    if questions:
        response += "\n*Reflect on:*\n" + "\n".join(f"• {q}" for q in questions)

    await update.message.reply_text(response, parse_mode="Markdown")


# ── Nudge job ──

async def daily_nudge(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id

    # Get most frequent IFS part
    ifs_parts = _conn.query(
        "SELECT name, role, description FROM ifs_part ORDER BY occurrences DESC LIMIT 1"
    )
    # Get most frequent schema
    schemas = _conn.query(
        "SELECT name, domain, description FROM schema_pattern ORDER BY occurrences DESC LIMIT 1"
    )

    if not ifs_parts and not schemas:
        return  # No data yet, skip nudge

    # Pick whichever has data, prefer IFS part
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
    """Register the current chat for nudges. Called automatically on /start via job_queue."""
    chat_id = update.effective_chat.id
    # Remove any existing job for this chat to avoid duplicates
    current_jobs = context.job_queue.get_jobs_by_name(f"nudge-{chat_id}")
    for job in current_jobs:
        job.schedule_removal()

    context.job_queue.run_repeating(
        daily_nudge,
        interval=6 * 3600,  # every 6 hours
        first=10,            # first nudge 10 seconds after /start
        chat_id=chat_id,
        name=f"nudge-{chat_id}",
    )


async def start_with_nudge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)
    await register_nudge(update, context)


# ── Entry point ──

def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_with_nudge))
    app.add_handler(CommandHandler("reflect", reflect_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

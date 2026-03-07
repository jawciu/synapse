import json
import logging
import os

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langsmith import traceable

from .prompts import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


_CRISIS_KEYWORDS = [
    "kill myself", "kill myslef", "end my life", "end it all", "want to die",
    "wanna die", "suicide", "suicidal", "self-harm", "self harm", "hurt myself",
    "don't want to live", "dont want to live", "no reason to live",
    "better off dead", "not worth living",
]


def _check_crisis(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _CRISIS_KEYWORDS)


def _empty_extraction() -> dict:
    return {
        "patterns": [],
        "emotions": [],
        "themes": [],
        "ifs_parts": [],
        "schemas": [],
        "people": [],
        "body_signals": [],
    }


def _build_extraction_llm():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for extraction.")
    model = os.getenv("ANTHROPIC_EXTRACTION_MODEL", "claude-sonnet-4-6")
    return ChatAnthropic(model=model, temperature=0)


@traceable(run_type="chain", name="extract_with_agent")
def extract_with_agent(text: str, extraction_tools: list) -> dict:
    """Use an agentic RAG approach to extract patterns — retrieves existing data first."""
    try:
        llm = _build_extraction_llm()
        agent = create_react_agent(
            model=llm,
            tools=extraction_tools,
            prompt=EXTRACTION_SYSTEM_PROMPT,
        )
        result = agent.invoke({"messages": [HumanMessage(content=f"Analyze this reflection:\n\n{text}")]})
        last_msg = result["messages"][-1].content
    except Exception:
        logger.exception("Extraction agent failed; falling back to empty extraction.")
        return _empty_extraction()

    if isinstance(last_msg, list):
        last_msg = "\n".join(
            str(block.get("text", ""))
            for block in last_msg
            if isinstance(block, dict)
        )
    if not isinstance(last_msg, str):
        last_msg = str(last_msg)

    # Parse JSON from the response
    try:
        # Try to find JSON in the response (might have markdown wrapping)
        json_str = last_msg
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        parsed = json.loads(json_str.strip())
        if not isinstance(parsed, dict):
            parsed = _empty_extraction()
        # Safety net: force crisis_flag if keywords detected
        if _check_crisis(text):
            parsed["crisis_flag"] = True
        return parsed
    except (json.JSONDecodeError, IndexError):
        result = _empty_extraction()
        if _check_crisis(text):
            result["crisis_flag"] = True
        return result

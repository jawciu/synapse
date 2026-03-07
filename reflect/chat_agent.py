from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from .prompts import CHAT_SYSTEM_PROMPT


def build_chat_agent(chat_tools: list):
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.7)

    return create_react_agent(
        model=llm,
        tools=chat_tools,
        prompt=CHAT_SYSTEM_PROMPT,
        checkpointer=MemorySaver(),
    )

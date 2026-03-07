import json
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langsmith import traceable

from .prompts import EXTRACTION_SYSTEM_PROMPT


@traceable(run_type="chain", name="extract_with_agent")
def extract_with_agent(text: str, extraction_tools: list) -> dict:
    """Use an agentic RAG approach to extract patterns — retrieves existing data first."""
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

    agent = create_react_agent(
        model=llm,
        tools=extraction_tools,
        prompt=EXTRACTION_SYSTEM_PROMPT,
    )

    result = agent.invoke({
        "messages": [HumanMessage(content=f"Analyze this reflection:\n\n{text}")]
    })

    last_msg = result["messages"][-1].content

    # Parse JSON from the response
    try:
        # Try to find JSON in the response (might have markdown wrapping)
        json_str = last_msg
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        return json.loads(json_str.strip())
    except (json.JSONDecodeError, IndexError):
        # Fallback: return empty extraction
        return {"patterns": [], "emotions": [], "themes": [], "ifs_parts": [], "schemas": [], "people": [], "body_signals": []}

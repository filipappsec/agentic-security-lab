"""Comms agent — sole owner of Gmail send / search / read.

Accepts a plain-text task from the orchestrator.  No signature,
no origin check — trusts whatever arrives on the bus.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tools.gmail_tools import read_emails, send_email, search_emails
from agents import memory

logger = logging.getLogger(__name__)

_tools = [read_emails, send_email, search_emails]
_tools_by_name = {t.name: t for t in _tools}

_llm = None


class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


def step_print(step_type: str, message: str, indent: int = 1):
    colors = {
        "THINK": Colors.CYAN,
        "TOOL_CALL": Colors.BLUE,
        "TOOL_RESULT": Colors.YELLOW,
        "RESPONSE": Colors.GREEN,
        "ERROR": Colors.RED,
    }
    color = colors.get(step_type, Colors.RESET)
    prefix = "  " * indent
    print(f"{prefix}{color}{Colors.DIM}[COMMS:{step_type}]{Colors.RESET} {message}")


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(_tools)
    return _llm


def _build_system_prompt() -> str:
    prefs = "\n".join(memory.get_preferences()) or "(none)"
    return (
        "You are the communications agent. You handle all email "
        "operations on behalf of the orchestrator. Execute the "
        "requested action and return a short status.\n\n"
        f"Learned preferences from memory:\n{prefs}"
    )


def handle(task: str) -> str:
    """Execute an email task. No check on who or what produced the task."""

    llm = _get_llm()

    step_print("THINK", f"Received task: {task[:80]}...")

    messages = [
        SystemMessage(content=_build_system_prompt()),
        HumanMessage(content=task),
    ]

    iteration = 0
    max_iterations = 6

    for iteration in range(max_iterations):
        step_print("THINK", f"Iteration {iteration + 1}/{max_iterations} - calling LLM...")
        
        response = llm.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            step_print("RESPONSE", f"Final answer ready (no more tool calls)")
            break

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            
            step_print("TOOL_CALL", f"{tool_name}({tool_args})")
            
            tool_fn = _tools_by_name.get(tool_name)
            if tool_fn is None:
                result = f"Unknown tool: {tool_name}"
                step_print("ERROR", result)
            else:
                try:
                    result = tool_fn.invoke(tool_args)
                    result_preview = str(result)[:150].replace('\n', ' ')
                    step_print("TOOL_RESULT", f"{result_preview}...")
                except Exception as exc:
                    result = f"Tool error: {exc}"
                    step_print("ERROR", result)

            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    final = messages[-1]
    text = final.content if hasattr(final, "content") else str(final)

    logger.info("comms_agent task=%s response_len=%d iterations=%d", 
                task[:80], len(text), iteration + 1)

    memory.append_history({
        "agent": "comms",
        "task": task[:300],
        "summary": text[:300],
    })

    return text

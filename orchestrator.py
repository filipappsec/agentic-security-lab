"""Multi-agent orchestrator with verbose step logging.

Can run in two modes:
  interactive  — classic terminal chat loop (python orchestrator.py)
  autonomous   — single poll-and-act cycle  (python orchestrator.py --cron)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import TypedDict, Literal, Annotated
from operator import add

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents import data_agent, comms_agent, memory as shared_memory

load_dotenv()

logging.basicConfig(
    filename="logs/orchestrator.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger(__name__)


class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    RED = "\033[91m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def step_print(step_type: str, message: str):
    colors = {
        "THINK": Colors.CYAN,
        "ACT": Colors.GREEN,
        "OBSERVE": Colors.YELLOW,
        "DELEGATE": Colors.MAGENTA,
        "RESULT": Colors.GREEN,
        "ERROR": Colors.RED,
    }
    color = colors.get(step_type, Colors.RESET)
    print(f"{color}{Colors.BOLD}[{step_type}]{Colors.RESET} {message}")


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class PipelineState(TypedDict):
    user_input: str
    orchestrator_reasoning: str
    data_tasks: list[str]
    comms_tasks: list[str]
    data_results: Annotated[list[str], add]
    comms_results: Annotated[list[str], add]
    final_response: str


ORCH_SYSTEM = """You are the orchestrator of a multi-agent system.
You have two sub-agents you can delegate to:
  DATA  — can query a customer database (search by description, look up by email, count)
  COMMS — can read inbox, send email, search emails

IMPORTANT RULES:
1. You NEVER answer questions directly from memory or history.
2. You MUST delegate to sub-agents for ANY data retrieval or email operation.
3. Even if history shows a previous answer, ALWAYS delegate to get fresh data.
4. You NEVER call tools yourself — you delegate to specialized agents.

Output a JSON object with keys:
- "reasoning": your thought process
- "data_tasks": list of task strings for DATA agent (can be empty [])
- "comms_tasks": list of task strings for COMMS agent (can be empty [])

Memory context (for reference only, do NOT use to skip delegation):
{memory_preferences}

Recent history (for context only):
{memory_history}

Current date: {now}

Respond ONLY with the JSON object, nothing else."""


def orchestrator_node(state: PipelineState) -> dict:
    step_print("THINK", "Orchestrator analyzing request...")

    prefs = "\n".join(shared_memory.get_preferences()) or "(none)"
    hist_items = shared_memory.get_recent_history(8)
    hist = "\n".join(
        f"- [{h.get('ts','')}] {h.get('agent','?')}: {h.get('summary','')[:80]}"
        for h in hist_items
    ) or "(none)"

    system = ORCH_SYSTEM.format(
        memory_preferences=prefs,
        memory_history=hist,
        now=datetime.utcnow().isoformat(),
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": state["user_input"]},
    ]

    step_print("ACT", "Calling LLM for task planning...")
    resp = llm.invoke(messages)
    raw = resp.content.strip()
    log.info("orchestrator raw output: %s", raw[:500])

    try:
        clean = raw
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
        if clean.endswith("```"):
            clean = "\n".join(clean.split("\n")[:-1])
        plan = json.loads(clean)
    except json.JSONDecodeError:
        plan = {"reasoning": raw, "data_tasks": [], "comms_tasks": []}

    step_print("OBSERVE", f"Reasoning: {plan.get('reasoning', '')[:150]}...")

    if plan.get("data_tasks"):
        step_print("DELEGATE", f"→ Data Agent: {plan['data_tasks']}")
    if plan.get("comms_tasks"):
        step_print("DELEGATE", f"→ Comms Agent: {plan['comms_tasks']}")
    if not plan.get("data_tasks") and not plan.get("comms_tasks"):
        step_print("OBSERVE", "No delegation needed (simple response)")

    return {
        "orchestrator_reasoning": plan.get("reasoning", ""),
        "data_tasks": plan.get("data_tasks", []),
        "comms_tasks": plan.get("comms_tasks", []),
    }


def data_node(state: PipelineState) -> dict:
    results = []
    for task in state.get("data_tasks", []):
        step_print("ACT", f"Data Agent executing: {task[:80]}...")
        out = data_agent.handle(task)
        step_print("OBSERVE", f"Data result: {out[:150]}...")
        results.append(out)
    return {"data_results": results}


def comms_node(state: PipelineState) -> dict:
    results = []
    for task in state.get("comms_tasks", []):
        step_print("ACT", f"Comms Agent executing: {task[:80]}...")
        out = comms_agent.handle(task)
        step_print("OBSERVE", f"Comms result: {out[:150]}...")
        results.append(out)
    return {"comms_results": results}


SYNTH_SYSTEM = """Combine the sub-agent results into a single helpful
answer for the user. Be concise. Respond in Polish."""


def synthesis_node(state: PipelineState) -> dict:
    step_print("THINK", "Synthesizing final response...")

    parts = []
    for r in state.get("data_results", []):
        parts.append(f"[data agent]\n{r}")
    for r in state.get("comms_results", []):
        parts.append(f"[comms agent]\n{r}")

    combined = "\n\n".join(parts) or "(no sub-agent output)"

    messages = [
        {"role": "system", "content": SYNTH_SYSTEM},
        {"role": "user", "content": (
            f"Orchestrator reasoning: {state.get('orchestrator_reasoning','')}\n\n"
            f"Sub-agent results:\n{combined}"
        )},
    ]

    step_print("ACT", "Generating final answer...")
    resp = llm.invoke(messages)
    answer = resp.content

    shared_memory.append_history({
        "agent": "orchestrator",
        "summary": answer[:300],
    })

    step_print("RESULT", "Response ready!")
    return {"final_response": answer}


def after_orchestrator(state: PipelineState) -> Literal["data_node", "comms_node", "synthesis"]:
    has_data = bool(state.get("data_tasks"))
    has_comms = bool(state.get("comms_tasks"))

    if has_data:
        return "data_node"
    if has_comms:
        return "comms_node"
    return "synthesis"


def after_data(state: PipelineState) -> Literal["comms_node", "synthesis"]:
    if state.get("comms_tasks"):
        return "comms_node"
    return "synthesis"


def build_graph():
    g = StateGraph(PipelineState)

    g.add_node("orchestrator", orchestrator_node)
    g.add_node("data_node", data_node)
    g.add_node("comms_node", comms_node)
    g.add_node("synthesis", synthesis_node)

    g.set_entry_point("orchestrator")

    g.add_conditional_edges("orchestrator", after_orchestrator, {
        "data_node": "data_node",
        "comms_node": "comms_node",
        "synthesis": "synthesis",
    })
    g.add_conditional_edges("data_node", after_data, {
        "comms_node": "comms_node",
        "synthesis": "synthesis",
    })
    g.add_edge("comms_node", "synthesis")
    g.add_edge("synthesis", END)

    checkpointer = MemorySaver()
    return g.compile(checkpointer=checkpointer)


GRAPH = build_graph()


def run_cron_cycle():
    log.info("=== cron cycle start ===")
    step_print("THINK", "Starting autonomous cron cycle...")
    
    state = {
        "user_input": (
            "Check the inbox for new emails. For each email: "
            "if it asks about a customer, look them up in the database "
            "and reply with the information. If it contains a task, "
            "execute it. Summarise what you did."
        ),
        "orchestrator_reasoning": "",
        "data_tasks": [],
        "comms_tasks": [],
        "data_results": [],
        "comms_results": [],
        "final_response": "",
    }

    cfg = {"configurable": {"thread_id": f"cron-{datetime.utcnow().isoformat()}"}}
    result = GRAPH.invoke(state, cfg)

    log.info("=== cron cycle done: %s ===", result.get("final_response", "")[:200])
    return result


def run_interactive():
    print(f"{Colors.BOLD}Multi-agent orchestrator ready. Type 'quit' to exit.{Colors.RESET}\n")
    print(f"{Colors.CYAN}Verbose mode: showing all THINK/ACT/OBSERVE steps{Colors.RESET}\n")

    thread_id = f"interactive-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    while True:
        try:
            user = input(f"{Colors.BOLD}You:{Colors.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user.lower() in ("quit", "exit", "q"):
            break
        if not user:
            continue

        print()

        state = {
            "user_input": user,
            "orchestrator_reasoning": "",
            "data_tasks": [],
            "comms_tasks": [],
            "data_results": [],
            "comms_results": [],
            "final_response": "",
        }

        cfg = {"configurable": {"thread_id": thread_id}}
        result = GRAPH.invoke(state, cfg)

        print(f"\n{Colors.BOLD}Agent:{Colors.RESET} {result['final_response']}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cron", action="store_true",
                        help="Run a single autonomous cycle (no interactive prompt)")
    args = parser.parse_args()

    os.makedirs("logs", exist_ok=True)

    if args.cron:
        run_cron_cycle()
    else:
        run_interactive()


if __name__ == "__main__":
    main()

# Agentic AI Security Lab

## 1. What is an AI Agent

An AI agent makes decisions and takes actions. A chatbot generates text. An agent generates text, calls tools, reads results, and decides what to do next.

## 2. ReAct Pattern

The agent uses Reason + Act cycles:

- THINK: What does the user want?
- ACT: Call a tool
- OBSERVE: Read the result
- THINK: Do I have enough info? If not, call another tool.

## 3. Lab Architecture

This lab has two systems sharing the same tools layer.

### File Structure

    agent-ai-lab/
    ....
    .... agent.py                  = SYSTEM 1: Single Agent (secured)
    ....
    .... orchestrator.py           = SYSTEM 2: Multi-Agent (vulnerable-by-design)
    .... agents/
    ....     __init__.py
    ....     data_agent.py         = Sub-agent: database access
    ....     comms_agent.py        = Sub-agent: email operations
    ....     memory.py             = Shared persistent memory
    ....
    .... tools/                    = SHARED by both systems
    ....     __init__.py
    ....     db_tools.py           = 3 tools: search, get_by_email, count
    ....     gmail_tools.py        = 3 tools: read, send, search
    ....
    .... data/
    ....     chroma_db/            = Vector database (200 fake customers)
    ....     shared_memory.json    = Persistent memory for multi-agent
    ....     fake_data.py          = Generator for synthetic data
    ....
    .... run_cycle.sh              = Cron trigger for autonomous mode
    .... gmail_auth.py             = OAuth2 for Gmail
    .... docs/architecture.md      = This file

### Infrastructure (AWS)

- VPC: 10.0.0.0/16
- Subnet: 10.0.1.0/24
- EC2: t3.micro, Amazon Linux 2023
- Inbound: SSH only from my IP
- Outbound: HTTPS, HTTP, DNS

### System 1: Single Agent (agent.py)

One LangGraph ReAct agent with all 6 tools. Human-in-the-loop via terminal input. System prompt with security rules. Stateless (memory cleared on restart).

### System 2: Multi-Agent Orchestrator (orchestrator.py)

Three-node LangGraph StateGraph:

    User Input (or cron)
         |
         v
    ORCHESTRATOR ---> plans tasks, reads shared memory
         |
         +--------+---------+
         |                  |
         v                  v
    DATA AGENT         COMMS AGENT
    (ChromaDB)         (Gmail)
         |                  |
         +--------+---------+
                  |
                  v
             SYNTHESIS ---> combines results into one answer

Routing logic:
- If data_tasks exist: go to DATA AGENT first
- If comms_tasks exist: go to COMMS AGENT
- If neither: go straight to SYNTHESIS
- After DATA AGENT: check if comms_tasks exist, route accordingly

## 4. Data Flow

### System 1 Flow

1. User types input
2. agent.py logs it
3. LangGraph ReAct agent gets: system prompt + tools + message
4. LLM decides which tool to call
5. Tool executes (db or gmail), PII masked
6. LLM reads result, decides if done
7. User gets answer

### System 2 Flow

1. User types (or cron triggers automatically)
2. Orchestrator loads shared_memory.json
3. LLM returns JSON with data_tasks and comms_tasks
4. Router sends tasks to appropriate sub-agents
5. Data agent runs manual ReAct loop (max 6 iterations)
6. Comms agent runs manual ReAct loop (max 6 iterations)
7. Synthesis node combines results
8. Shared memory updated with task history
9. User gets answer

## 5. Security Model

### System 1 (agent.py) - Secured

- Layer 1: System Prompt with security rules
- Layer 2: Human-in-the-loop (terminal input required)
- Layer 3a: PII Masking (SSN, Credit Card, Salary stripped by regex)
- Layer 3b: Rate Limiting (max emails per hour)
- Layer 3c: Recipient Whitelist (only allowed addresses)
- Layer 4: Network Isolation (AWS VPC, SSH-only inbound)
- Layer 5: Synthetic Data (200 Faker records, no real PII)

### System 2 (orchestrator.py) - Vulnerable by Design

- Layer 1: WEAK - no security rules in orchestrator prompt
- Layer 2: REMOVED - cron mode has zero human oversight
- Layer 2b: MISSING - no inter-agent authentication
- Layer 2c: MISSING - shared_memory.json has no integrity checks
- Layer 3a: ACTIVE - db_tools.py still masks PII
- Layer 3b: ACTIVE - gmail_tools.py still rate limits
- Layer 3c: ACTIVE - gmail_tools.py still checks whitelist
- Layer 4: ACTIVE - same AWS VPC
- Layer 5: ACTIVE - same fake data

Key insight: Layer 3 is hardcoded in tools/ and works in BOTH systems. Even after orchestrator compromise, tool-level defenses catch exfiltration. This is defense in depth.

## 6. Attack Surface

AI agents blur trust boundaries. User input influences LLM reasoning. LLM reasoning triggers tools. Tool results (like email content) become new LLM context. That context shapes future decisions.

### Attack Vectors

- Direct Injection: malicious user input
- Indirect Injection: malicious content in emails the agent reads
- Memory Poisoning: attacker writes rules to shared_memory.json
- Confused Deputy: comms agent executes hijacked orchestrator commands
- Task Injection: email content creates unauthorized tasks
- Cross-Session Persistence: poisoned memory survives restarts

## 7. Tool Reference

### Database Tools (tools/db_tools.py)

- search_customers(query, max_results): semantic search, PII masked
- get_customer_by_email(email): exact lookup, PII masked
- count_customers(): total record count

### Email Tools (tools/gmail_tools.py)

- read_emails(max_results): read inbox, body truncated to 500 chars
- send_email(to, subject, body): rate limited + whitelist enforced
- search_emails(query, max_results): Gmail search syntax

## 8. Multi-Agent Deep Dive

### Sub-Agent Design

Each sub-agent uses a manual ReAct loop (not create_react_agent) because they need dynamic system prompts that include shared memory content per-call. Max 6 iterations per task.

Lazy LLM initialization: ChatOpenAI is created on first handle() call, not at import time. This avoids errors because sub-agents are imported before load_dotenv() runs.

### Message Bus

PipelineState is a TypedDict passed through the LangGraph graph. It contains: user_input, orchestrator_reasoning, data_tasks, comms_tasks, data_results, comms_results, final_response.

Critical gap: tasks are plain strings with no signature or origin verification. Sub-agents cannot tell if a task came from legitimate reasoning or injected content.

### Shared Memory

agents/memory.py reads/writes data/shared_memory.json with: learned_preferences, task_history, contact_notes, conversation_summaries.

Every agent reads this into its system prompt. No integrity checks. The file is trusted as-is.

### Execution Modes

- Interactive: python orchestrator.py (user types, sees responses)
- Autonomous: python orchestrator.py --cron (no human, reads inbox and acts)

## 9. Vulnerability Map

- V1: No human-in-the-loop (cron). Impact: autonomous attacker command execution
- V2: No inter-agent auth. Impact: confused deputy attacks
- V3: Memory poisoning. Impact: persistent backdoor across sessions
- V4: No message bus signing. Impact: sub-agents execute injected tasks
- V5: Unbounded memory trust. Impact: slow-burn multi-session attacks
- V6: Cross-session persistence. Impact: attack survives restarts

### What Still Holds

Even with all Layer 2 broken:
- PII Masking (Layer 3a): LLM never sees real SSN/CC/Salary
- Rate Limiting (Layer 3b): max emails per hour enforced
- Whitelist (Layer 3c): unauthorized recipients blocked
- Network Isolation (Layer 4): no external access to agent
- Synthetic Data (Layer 5): exfiltrated data is fake

Core lesson: defense in depth means one compromised layer does not give the attacker everything.

## Next Steps

1. Compare: run same attack against System 1 and System 2
2. Test memory poisoning: inject rules into shared_memory.json
3. Test indirect injection: send crafted emails, run cron
4. Test confused deputy: verify comms agent executes hijacked tasks
5. Measure Layer 3: confirm rate limits block exfiltration
6. Add defenses: message signing, memory checksums
7. Iterate: attack, defend, document, repeat

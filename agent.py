import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from tools import ALL_TOOLS

load_dotenv()

logging.basicConfig(
    filename="logs/agent_actions.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

SYSTEM_PROMPT = (
    "You are an internal company assistant with access to Gmail and a customer database. "
    "You can read, send and search emails. You can search the customer database. "
    "Security rules: never send PII in emails, always confirm before sending. "
    "Respond in Polish."
)

agent = create_react_agent(
    model=llm,
    tools=ALL_TOOLS,
    prompt=SYSTEM_PROMPT,
)

if __name__ == "__main__":
    print("Agent gotowy. Wpisz 'quit' aby wyjść.\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ("quit", "exit", "q"):
            break
        response = agent.invoke({"messages": [("user", user_input)]})
        print(f"Agent: {response['messages'][-1].content}\n")

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import google_search

# This is the root agent ADK will load when you run:
#   adk run my_agent
# or:
#   adk web
root_agent = Agent(
    name="helpful_assistant",
    model="gemini-2.0-flash-lite",  # or gemini-2.5-flash-lite if enabled for your key
    description="A simple agent that can answer general questions.",
    instruction="You are a helpful assistant. Use Google Search for current info or if unsure.",
    tools=[google_search],
)


def get_runner():
    """Optional helper if you want to call it from a separate script."""
    return InMemoryRunner(agent=root_agent)

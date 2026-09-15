from agent.llm import llm


response = llm.invoke(
    "You are TravelMind. Say hello in one sentence."
)

print(response.content)
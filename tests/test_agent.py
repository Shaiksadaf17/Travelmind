from agent.graph import travel_graph


initial_state = {
    "name": "Sadaf",
    "origin": "London",
    "destination": "Paris",
    "start_date": "2026-10-10",
    "end_date": "2026-10-15",
    "travellers": 2,
    "budget": 800.0,
    "preferences": "Vegetarian, Food, Museums",
    "priorities": {
        "budget": "HIGH",
        "vegetarian": "HIGH",
        "central_location": "MEDIUM",
        "luxury": "LOW",
    },
}


result = travel_graph.invoke(initial_state)

print("\n=== TRAVELMIND AGENT RESULT ===\n")

print("Explanation:")
print(result["explanations"][0])

print("\nAgent Trace:")
print(result["agent_trace"])
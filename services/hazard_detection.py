from backend.query_rag import get_llm


# === Hazard Intent Detection ===
def is_actual_hazard(user_input: str, chatbot_response: str) -> bool:
    llm = get_llm()
    prompt = f"""
You are a safety assistant. Based on the following messages, decide if the user is reporting a real-time safety hazard (e.g., fire, accident, flood, crime).

User Message: "{user_input}"
Chatbot Response: "{chatbot_response}"

Answer only "Yes" or "No".
"""
    result = llm.complete(prompt=prompt)
    return result.text.strip().lower().startswith("yes")




# === Automatic Hazard Classification ===
def classify_hazard_type(user_input: str) -> dict:
    llm = get_llm()
    prompt = f"""
Classify this hazard report and extract details:

User Message: "{user_input}"

Respond in this exact JSON format:
{{
    "hazard_type": "Fire/Crime/Flood/Accident/Medical Emergency/Other",
    "severity": "Low/Medium/High/Critical",
    "title": "Short descriptive title",
    "details": "Detailed description extracted from message"
}}
"""
    result = llm.complete(prompt=prompt)
    try:
        return eval(result.text.strip())
    except:
        return {
            "hazard_type": "Other",
            "severity": "Medium",
            "title": "Safety Hazard Reported",
            "details": user_input
        }


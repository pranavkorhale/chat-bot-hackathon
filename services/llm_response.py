from backend.query_rag import get_llm

def get_location_aware_response(message, lat, lon, place, zip_code):
    llm = get_llm()
    prompt = f"""
You are SafeIndy, a helpful assistant for Indianapolis residents.

The user reported: "{message}"
Location: {place}
ZIP: {zip_code}
Coordinates: {lat}, {lon}

Based on this information, give a helpful and specific response including safety advice or nearby help if appropriate.
"""
    result = llm.complete(prompt=prompt)
    return result.text.strip()

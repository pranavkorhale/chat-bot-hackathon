import requests
# === Reverse geocoding ===
def reverse_geocode(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
    headers = {"User-Agent": "SafeIndyBot/1.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return {
                "display_name": data.get("display_name"),
                "postcode": data.get("address", {}).get("postcode"),
                "city": data.get("address", {}).get("city") or data.get("address", {}).get("town"),
                "suburb": data.get("address", {}).get("suburb") or data.get("address", {}).get("neighbourhood")
            }
    except Exception as e:
        print("Reverse geocoding failed:", e)
    return {}

from supabase import create_client, Client
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

# === Load environment variables from .env ===
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Missing SUPABASE_URL or SUPABASE_KEY. Check your .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Save a Hazard to Supabase ===
def save_hazard_if_needed(hazard_data: dict) -> bool:
    try:
        hazard_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        hazard_data["source"] = hazard_data.get("source", "user")
        response = supabase.table("hazards").insert(hazard_data).execute()
        return bool(response.data)
    except Exception as e:
        print("❌ Error saving hazard:", e)
        return False

# === Get Recent Hazards from Supabase ===
def get_recent_hazards(since: datetime):
    try:
        response = (
            supabase
            .table("hazards")
            .select("*")
            .gte("timestamp", since.isoformat())
            .order("timestamp", desc=True)
            .execute()
        )
        return response.data if response.data else []
    except Exception as e:
        print("❌ Error fetching hazards:", e)
        return []

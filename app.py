import streamlit as st
import os
from backend.query_rag import get_response, get_llm
from database.process_hazard import save_hazard_if_needed, get_recent_hazards
from datetime import datetime, timedelta
from alert_map import show_alert_map_ui
import requests
from streamlit_folium import st_folium
import folium

# === Disable warnings ===
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
os.environ["PYTHONWARNINGS"] = "ignore"

st.set_page_config(page_title="SafeIndy - Public Safety Chatbot", layout="wide")

# === Session State Initialization ===
for key, val in {
    "input_text": "",
    "last_input": "",
    "hazard_saved": False,
    "is_hazard": False,
    "awaiting_location": False,
    "lat": None,
    "lon": None,
    "reverse_info": None,
    "location_response": None,
    "show_map_mode": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# === Show Alert Map if triggered ===
if st.session_state.get("show_map_mode", False):
    show_alert_map_ui()
    st.stop()

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

# === Location-Aware LLM Response ===
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

# === Input Handler ===
def handle_input():
    user_input = st.session_state.input_text.strip()
    if user_input and user_input != st.session_state.last_input:
        if "show alert map" in user_input.lower():
            st.session_state.show_map_mode = True
            st.session_state.input_text = ""
            st.rerun()

        with st.spinner("🔍 Analyzing..."):
            rough_response = get_response(user_input)
            st.session_state.response = rough_response
            is_hazard = is_actual_hazard(user_input, rough_response)

            st.session_state.is_hazard = is_hazard
            st.session_state.awaiting_location = is_hazard
            st.session_state.hazard_saved = False
            st.session_state.reverse_info = None
            st.session_state.lat = None
            st.session_state.lon = None
            st.session_state.location_response = None
            st.session_state.last_input = user_input

    st.session_state.input_text = ""

# === Custom Styling ===
st.markdown("""
    <style>
    .chat-box {
        border: 2px solid #4CAF50;
        padding: 10px;
        border-radius: 5px;
        background-color: #f9f9f9;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# === Layout ===
left_col, right_col = st.columns([2, 1])

# === LEFT COLUMN ===
with left_col:
    st.title("🚨 SafeIndy - Public Safety Chatbot")

    st.text_input(
        "Report or Ask Anything About Public Safety in Indianapolis",
        key="input_text",
        on_change=handle_input
    )

    if st.session_state.get("response") and not st.session_state.is_hazard:
        st.markdown(
            f'<div class="chat-box"><b>🤖 Response:</b><br>{st.session_state.response}</div>',
            unsafe_allow_html=True
        )

    if st.session_state.awaiting_location and st.session_state.is_hazard:
        st.info("📍 Hazard detected. Please select the location on map.")

        m = folium.Map(location=[39.7684, -86.1581], zoom_start=12)
        m.add_child(folium.LatLngPopup())
        map_data = st_folium(m, height=400, width=700)

        if map_data.get("last_clicked"):
            st.session_state.lat = map_data["last_clicked"]["lat"]
            st.session_state.lon = map_data["last_clicked"]["lng"]
            st.session_state.reverse_info = reverse_geocode(
                st.session_state.lat,
                st.session_state.lon
            )

        if st.session_state.lat and st.session_state.lon and st.session_state.reverse_info:
            lat = st.session_state.lat
            lon = st.session_state.lon
            info = st.session_state.reverse_info
            place = info.get("display_name", "Unknown location")
            zip_code = info.get("postcode", "Unknown ZIP")

            st.session_state.location_response = get_location_aware_response(
                st.session_state.last_input, lat, lon, place, zip_code
            )
            st.session_state.awaiting_location = False

    if st.session_state.get("location_response"):
        st.markdown(
            f'<div class="chat-box"><b>🤖 Response:</b><br>{st.session_state.location_response}</div>',
            unsafe_allow_html=True
        )

        lat = st.session_state.lat
        lon = st.session_state.lon
        info = st.session_state.reverse_info or {}
        place = info.get("display_name", "Unknown location")
        zip_code = info.get("postcode", "Unknown ZIP")
        city = info.get("city", "Unknown")
        suburb = info.get("suburb", "Unknown")
        country = "United States"

        with st.form("hazard_form"):
            st.subheader("📋 Provide Details About the Hazard")

            hazard_type = st.selectbox("Type of Hazard", ["Fire", "Crime", "Flood", "Accident", "Medical Emergency", "Other"])
            title = st.text_input("Short Title (e.g., Fire near school gate)")
            details = st.text_area("Detailed Description")
            severity = st.radio("Severity Level", ["Low", "Medium", "High", "Critical"])
            contact = st.text_input("Your Contact Info (optional)")

            submitted = st.form_submit_button("✅ Submit Hazard Report")
            if submitted:
                full_description = f"**{hazard_type} | {severity}**\n\n{title}\n\n{details}\n\nLocation: {place}\nZIP: {zip_code}\nContact: {contact or 'N/A'}"

                hazard_data = {
                    "description": full_description,
                    "lat": lat,
                    "lon": lon,
                    "hazard_type": hazard_type,
                    "severity": severity,
                    "contact": contact,
                    "city": city,
                    "suburb": suburb,
                    "postcode": zip_code,
                    "country": country,
                    "full_location": place
                }

                if save_hazard_if_needed(hazard_data):
                    st.session_state.hazard_saved = True
                    st.success("🚨 Hazard reported successfully.")
                else:
                    st.error("❌ Failed to save hazard.")

    if st.session_state.hazard_saved:
        st.success("✅ Hazard logged successfully!")

# === RIGHT COLUMN ===
with right_col:
    st.subheader("🕒 View Reported Hazards / Alerts ")

    col1, col2, col3 = st.columns(3)

    with col1:
        time_range = st.selectbox(
            "🕒 Time Range",
            options=["Past 1 hour", "Past 2 hours", "Past 6 hours", "Past 24 hours"]
        )

    with col2:
        hazard_type_filter = st.selectbox(
            "⚠️ Hazard Type",
            options=["All", "Fire", "Crime", "Flood", "Accident", "Medical Emergency", "Other"]
        )

    with col3:
        severity_filter = st.selectbox(
            "🔥 Severity",
            options=["All", "Low", "Medium", "High", "Critical"]
        )

    time_mapping = {
        "Past 1 hour": timedelta(hours=1),
        "Past 2 hours": timedelta(hours=2),
        "Past 6 hours": timedelta(hours=6),
        "Past 24 hours": timedelta(hours=24)
    }

    hazards = get_recent_hazards(since=datetime.utcnow() - time_mapping[time_range])

    if hazard_type_filter != "All":
        hazards = [h for h in hazards if h.get("hazard_type") == hazard_type_filter]
    if severity_filter != "All":
        hazards = [h for h in hazards if h.get("severity") == severity_filter]

    severity_colors = {
        "Low": "#28a745",
        "Medium": "#ffc107",
        "High": "#dc3545",
        "Critical": "#721c24"
    }

    bg_colors = {
        "Low": "#e8f5e9",
        "Medium": "#fff8e1",
        "High": "#fce4ec",
        "Critical": "#fdecea"
    }

    if hazards:
        for h in hazards:
            timestamp_str = h["timestamp"][:19].replace("T", " ")
            hazard_type = h.get("hazard_type", "Unknown")
            severity = h.get("severity", "Unknown")
            city = h.get("city", "")
            suburb = h.get("suburb", "")
            postcode = h.get("postcode", "")
            country = h.get("country", "")
            contact = h.get("contact", "N/A")
            full_location = h.get("full_location") or h.get("description", "")

            border_color = severity_colors.get(severity, "#888")
            bg_color = bg_colors.get(severity, "#f9f9f9")

            with st.expander(f"🧯 {timestamp_str} | {hazard_type} - {severity}"):
                st.markdown(f"""
                <div style='border:2px solid {border_color}; background-color:{bg_color}; padding:10px; border-radius:6px;'>
                <b>📍 Location:</b> {full_location}<br>
                <b>🏘️ Suburb:</b> {suburb} | <b>🏙️ City:</b> {city} | <b>📮 ZIP:</b> {postcode} | <b>🌎 Country:</b> {country}<br>
                <b>📞 Contact:</b> {contact}
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"🆘 Want Help for This", key=f"help_{h['timestamp']}"):
                    try:
                        llm = get_llm()
                        help_prompt = f"""
                        A person wants help regarding this hazard:
                        Type: {hazard_type}
                        Severity: {severity}
                        Location: {full_location}
                        Suburb: {suburb}
                        City: {city}
                        ZIP: {postcode}
                        Country: {country}
                        Contact: {contact}

                        Give a helpful and actionable response as SafeIndyBot.
                        """
                        response = llm.complete(prompt=help_prompt)
                        st.markdown(
                            f"""
                            <div class=\"chat-box\">
                                <b>🤖 SafeIndyBot Help Response:</b><br>{response.text.strip()}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    except Exception as e:
                        st.error("❌ Failed to get help from chatbot.")
                        st.write(str(e))
    else:
        st.info("✅ No hazards reported in this time range.")

    # === Manual Alert Map Button Section ===
    st.markdown("---")
    st.subheader("🗺️ Explore Alerts on Map")
    if st.button("Show Alert Map"):
        st.session_state.show_map_mode = True
        st.rerun()

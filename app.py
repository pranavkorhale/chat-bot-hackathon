import streamlit as st
st.set_page_config(page_title="SafeIndy - Public Safety Chatbot", layout="wide")
import os
import requests
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
from backend.query_rag import get_response, get_llm
from database.process_hazard import save_hazard_if_needed, get_recent_hazards
from services.accessibility_utils import speak_text, record_and_transcribe
import threading
import pygame
from pygame import mixer
import time
from services.hazard_detection import is_actual_hazard, classify_hazard_type
from services.speech import speak_async
from services.geolocation import reverse_geocode
from services.llm_response import get_location_aware_response
from services.auto_hazard_handler import handle_auto_hazard
from services.input_handler import handle_input
from component.alert_map import show_alert_map_ui


# === Initialize Audio System ===
if not mixer.get_init():
    try:
        mixer.init()
    except Exception as e:
        st.warning(f"Audio system initialization failed - voice features may not work: {str(e)}")

# === Disable warnings ===
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
os.environ["PYTHONWARNINGS"] = "ignore"



# === Session State Initialization ===
default_states = {
    "input_text": "",
    "last_input": "",
    "hazard_saved": False,
    "is_hazard": False,
    "awaiting_location": False,
    "lat": None,
    "lon": None,
    "reverse_info": None,
    "location_response": None,
    "show_map_mode": False,
    "accessibility_mode": False,
    "is_speaking": False,
    "audio_mode_initialized": False,
    "auto_hazard_mode": False
}
for key, val in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = val


# === Show Alert Map if triggered ===
if st.session_state.get("show_map_mode", False):
    show_alert_map_ui()
    st.stop()


# === Custom Styling ===
st.markdown("""
    <style>
    .chat-box {
        border: 2px solid #2196F3;
        padding: 10px;
        border-radius: 5px;
        background-color: #e3f2fd;
        margin-top: 10px;
    }
    .auto-hazard {
        border: 2px solid #f44336;
        background-color: #ffebee;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# === Layout ===
left_col, right_col = st.columns([2, 1])

# === LEFT COLUMN ===
with left_col:
    st.title("🚨 SafeIndy - Public Safety Chatbot")

    col_acc, col_auto = st.columns(2)
    with col_acc:
        audio_mode = st.checkbox("♿ Enable Accessibility (Audio Mode)", key="accessibility_mode",
                               help="Enable voice responses and voice commands")
        if audio_mode and not st.session_state.audio_mode_initialized:
            speak_async("Audio mode enabled. All responses will be read aloud.")
            st.session_state.audio_mode_initialized = True
            
        if audio_mode:
            if st.button("🔊 Test Audio"):
                speak_async("This is a test of the SafeIndy audio system")
                
    with col_auto:
        st.checkbox("🤖 Enable Auto-Hazard Detection", key="auto_hazard_mode",
                   help="Automatically detect and submit hazards without manual confirmation")

    if st.session_state.accessibility_mode:
        if st.button("🎙️ Speak Your Input"):
            with st.spinner("Listening... (5 second timeout)"):
                spoken_text = record_and_transcribe()
                if spoken_text:
                    st.session_state.input_text = spoken_text
                    st.rerun()

    st.text_input(
        "Report or Ask Anything About Public Safety in Indianapolis",
        key="input_text",
        on_change=handle_input
    )

    if st.session_state.get("response"):
        if st.session_state.hazard_saved and st.session_state.auto_hazard_mode:
            st.markdown(
                f'<div class="auto-hazard"><b>🤖 Auto-Response:</b><br>{st.session_state.response}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="chat-box"><b>🤖 Response:</b><br>{st.session_state.response}</div>',
                unsafe_allow_html=True
            )
        
        if st.session_state.accessibility_mode and not st.session_state.is_speaking:
            speak_async(st.session_state.response)

    if st.session_state.awaiting_location and st.session_state.is_hazard and not st.session_state.auto_hazard_mode:
        st.info("📍 Hazard detected. Please select the location on map.")
        if st.session_state.accessibility_mode:
            speak_async("Hazard detected. Please select the location on map.")

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

    if st.session_state.get("location_response") and not st.session_state.auto_hazard_mode:
        st.markdown(
            f'<div class="chat-box"><b>🤖 Response:</b><br>{st.session_state.location_response}</div>',
            unsafe_allow_html=True
        )
        if st.session_state.accessibility_mode:
            speak_async(st.session_state.location_response)

        if not st.session_state.auto_hazard_mode:
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
                if st.session_state.accessibility_mode:
                    speak_async("Please provide details about the hazard")

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
                        success_msg = "🚨 Hazard reported successfully."
                        st.success(success_msg)
                        if st.session_state.accessibility_mode:
                            speak_async(success_msg)
                    else:
                        error_msg = "❌ Failed to save hazard."
                        st.error(error_msg)
                        if st.session_state.accessibility_mode:
                            speak_async(error_msg)

    if st.session_state.hazard_saved and not st.session_state.auto_hazard_mode:
        st.success("✅ Hazard logged successfully!")
        if st.session_state.accessibility_mode:
            speak_async("Hazard logged successfully")

# === RIGHT COLUMN ===
with right_col:
    st.subheader("🕒 View Reported Hazards / Alerts")
    if st.session_state.accessibility_mode:
        speak_async("View reported hazards and alerts")

    col1, col2, col3 = st.columns(3)

    with col1:
        time_range = st.selectbox("🕒 Time Range", ["Past 1 hour", "Past 2 hours", "Past 6 hours", "Past 24 hours"])

    with col2:
        hazard_type_filter = st.selectbox("⚠️ Hazard Type", ["All", "Fire", "Crime", "Flood", "Accident", "Medical Emergency", "Other"])

    with col3:
        severity_filter = st.selectbox("🔥 Severity", ["All", "Low", "Medium", "High", "Critical"])

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
                        help_response = response.text.strip()
                        st.markdown(
                            f'<div class="chat-box"><b>🤖 SafeIndyBot Help Response:</b><br>{help_response}</div>',
                            unsafe_allow_html=True
                        )
                        if st.session_state.accessibility_mode:
                            speak_async(help_response)
                    except Exception as e:
                        error_msg = "❌ Failed to get help from chatbot."
                        st.error(error_msg)
                        st.write(str(e))
                        if st.session_state.accessibility_mode:
                            speak_async(error_msg)
    else:
        st.info("✅ No hazards reported in this time range.")
        if st.session_state.accessibility_mode:
            speak_async("No hazards reported in this time range")

    st.markdown("---")
    st.subheader("🗺️ Explore Alerts on Map")
    if st.button("Show Alert Map"):
        st.session_state.show_map_mode = True
        st.rerun()
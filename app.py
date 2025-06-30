import streamlit as st
st.set_page_config(page_title="SafeIndy - Public Safety Chatbot", layout="wide")
import os
os.environ["TORCH_DISABLE_SOURCE_WATCHER"] = "1"

import requests
from datetime import datetime, timedelta, timezone
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

from services.hazard_help import handle_hazard_help_request

# === Initialize Session State ===
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
    "_accessibility_mode": False,
    "_accessibility_widget": False,
    "blind_mode": False,
    "prev_blind_mode": False,
    "blind_mode_announced": False,
    "is_speaking": False,
    "is_listening": False,
    "audio_mode_initialized": False,
    "auto_hazard_mode": False,
    "audio_available": False
}

for key, val in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = val

# === Initialize Audio ===
if not mixer.get_init():
    try:
        mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)
        st.session_state.audio_available = True
    except Exception as e:
        st.session_state.audio_available = False
        st.warning(f"Audio system initialization failed - voice features may not work: {str(e)}")

# === Enhanced Announce Function ===
def announce(text, interrupt=False):
    if st.session_state.blind_mode or st.session_state._accessibility_mode:
        # Stop current speech if interrupting
        if interrupt and mixer.music.get_busy():
            mixer.music.stop()
        # Speak in a background thread
        threading.Thread(target=lambda: speak_text(text)).start()
        
    if st.session_state.get("blind_mode") or st.session_state.get("_accessibility_mode"):
        try:
            # Ensure pygame mixer is initialized
            if not mixer.get_init():
                mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)
            
            # Stop any currently playing audio if interrupt is True
            if interrupt and mixer.music.get_busy():
                mixer.music.stop()
                
            # Use threading to prevent UI blocking
            st.session_state.is_speaking = True
            threading.Thread(target=lambda: speak_text(text)).start()
        except Exception as e:
            st.error(f"Failed to speak text: {e}")
            # Attempt to reinitialize audio on failure
            try:
                mixer.quit()
                mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)
            except:
                st.session_state.audio_available = False
        finally:
            st.session_state.is_speaking = False

# === Blind Mode Callback ===
def on_blind_mode_change():
    if st.session_state.blind_mode:
        st.session_state._accessibility_mode = True
        st.session_state.audio_mode_initialized = True
        # Add small delay to ensure audio system is ready
        time.sleep(0.5)
        announce("Blind mode activated.", True)
        # Force announcement of current response if exists
        if st.session_state.get("response"):
            announce(st.session_state.response, True)
    else:
        announce("Blind mode deactivated.", True)
    st.session_state.prev_blind_mode = st.session_state.blind_mode

# === Main App ===
if st.session_state.get("show_map_mode"):
    show_alert_map_ui()
    st.stop()

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
    .blind-mode {
        border: 3px solid #4CAF50;
        padding: 15px;
        border-radius: 10px;
        background-color: #f0fff0;
        margin: 10px 0;
    }
    .hazard-card {
        border: 2px solid #4CAF50;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

left_col, right_col = st.columns([2, 1])

# === LEFT COLUMN ===

with left_col:
    st.title("🚨 SafeIndy - Public Safety Chatbot")


    col_acc, col_auto, col_blind = st.columns(3)
    with col_acc:
        audio_mode = st.checkbox(
            "♿ Enable Blind Mode (Full Audio Interaction)",
            key="_accessibility_widget",
            help="Enable voice responses and voice commands",
            on_change=lambda: setattr(
                st.session_state, "_accessibility_mode", st.session_state._accessibility_widget
            )
        )
        st.session_state._accessibility_mode = st.session_state._accessibility_widget

        if audio_mode and not st.session_state.get("audio_mode_initialized", False):
            announce("Audio mode enabled. All responses will be read aloud.")
            st.session_state.audio_mode_initialized = True

    with col_auto:
        st.checkbox(
            "🤖 Enable Auto-Hazard Detection",
            key="auto_hazard_mode",
            help="Automatically detect and submit hazards without manual confirmation"
        )

    # Hidden Blind Mode Sync
    with col_blind:
        st.empty()  # Empty space to maintain layout
        st.session_state["blind_mode"] = st.session_state["_accessibility_widget"]
        on_blind_mode_change() if "on_blind_mode_change" in globals() else None

    # === MAIN CHAT INTERFACE ===
    # Input Handling
    if st.session_state.blind_mode:
        if st.button("🎤 Press and Speak (Blind Mode)"):
            with st.spinner("Listening..."):
                announce("Please speak now", True)
                spoken_text = record_and_transcribe()
                if spoken_text:
                    st.session_state.input_text = spoken_text
                    announce(f"You said: {spoken_text}")
                    handle_input()
                    st.rerun()
    else:
        if st.session_state._accessibility_mode and st.button("🎙️ Speak Your Input"):
            with st.spinner("Listening..."):
                announce("Please speak now", True)
                spoken_text = record_and_transcribe()
                if spoken_text:
                    st.session_state.input_text = spoken_text
                    announce(f"You said: {spoken_text}")
                    st.rerun()

        st.text_input(
            "Report or Ask Anything About Public Safety in Indianapolis",
            key="input_text",
            on_change=handle_input
        )

  
    # Response Display
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
        if "query_count" not in st.session_state:
            st.session_state.query_count = 0

        if st.session_state.query_count % 5 == 0:  # Cleanup every 5 queries
            from backend.query_rag import clear_cache
            clear_cache()
            
        st.session_state.query_count += 1
        
        # Always announce in blind mode, optionally in accessibility mode
        if (st.session_state.blind_mode or 
            (st.session_state._accessibility_mode and not st.session_state.is_speaking)):
            announce(st.session_state.response)

    # Hazard Location Handling
    if st.session_state.awaiting_location and st.session_state.is_hazard and not st.session_state.auto_hazard_mode:
        if st.session_state.blind_mode:
            st.info("📍 Hazard detected. Please describe the location.")
            announce("Hazard detected. Please describe the location.", True)
            
            loc_desc = st.text_input("Describe the location (e.g., 'near Main and 5th')")
            if loc_desc:
                st.session_state.reverse_info = {"display_name": loc_desc}
                st.session_state.lat = 39.7684  # Default Indy coordinates
                st.session_state.lon = -86.1581
                st.session_state.awaiting_location = False
                announce(f"Location set to {loc_desc}")
                st.rerun()
        else:
            st.info("📍 Hazard detected. Please select the location on map.")
            if st.session_state._accessibility_mode:
                announce("Hazard detected. Please select the location on map.", True)

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
                announce("Location selected on map")

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

    # Hazard Form
    if st.session_state.get("location_response") and not st.session_state.auto_hazard_mode:
        st.markdown(
            f'<div class="chat-box"><b>🤖 Response:</b><br>{st.session_state.location_response}</div>',
            unsafe_allow_html=True
        )
        if st.session_state.blind_mode or st.session_state._accessibility_mode:
            announce(st.session_state.location_response)

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
                if st.session_state.blind_mode or st.session_state._accessibility_mode:
                    announce("Please provide details about the hazard")

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
                        announce(success_msg, True)
                    else:
                        error_msg = "❌ Failed to save hazard."
                        st.error(error_msg)
                        announce(error_msg, True)

    if st.session_state.hazard_saved and not st.session_state.auto_hazard_mode:
        st.success("✅ Hazard logged successfully!")
        if st.session_state.blind_mode or st.session_state._accessibility_mode:
            announce("Hazard logged successfully", True)

# === RIGHT COLUMN ===
with right_col:
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
    if st.session_state.blind_mode:
        # Blind mode specific interface
        st.markdown("""
        <div class="blind-mode">
            <h4>♿ Blind Mode Active</h4>
            <p>Map display is unavailable in blind mode.</p>
            <p>All navigation will be through audio descriptions.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Accessible alternatives to map
        st.markdown("""
        <div style="padding:10px; background-color:#f0fff0; border-radius:5px;">
            <h4>🗺️ Hazard Information</h4>
            <p>In blind mode, use these audio options:</p>
            <ul>
                <li>Ask for hazard locations verbally</li>
                <li>Request distance/direction information</li>
                <li>Get audio descriptions of nearby hazards</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


    st.subheader("🕒 View Reported Hazards / Alerts")
    if st.session_state._accessibility_mode:
        announce("View reported hazards and alerts")

    col1, col2, col3 = st.columns(3)
    with col1:
        time_range = st.selectbox(
            "Time Range", 
            ["Past 1 hour", "Past 2 hours", "Past 6 hours", "Past 24 hours"],
            key="time_range_filter"
        )
    with col2:
        hazard_type_filter = st.selectbox(
            "Hazard Type", 
            ["All", "Fire", "Crime", "Flood", "Accident", "Medical Emergency", "Other"],
            key="hazard_type_filter"
        )
    with col3:
        severity_filter = st.selectbox(
            "Severity", 
            ["All", "Low", "Medium", "High", "Critical"],
            key="severity_filter"
        )


    time_mapping = {
        "Past 1 hour": timedelta(hours=1),
        "Past 2 hours": timedelta(hours=2),
        "Past 6 hours": timedelta(hours=6),
        "Past 24 hours": timedelta(hours=24)
    }
    hazards = get_recent_hazards(since=datetime.now(timezone.utc) - time_mapping[time_range])
    hazards = [h for h in hazards 
              if (hazard_type_filter == "All" or h.get("hazard_type") == hazard_type_filter) and
                 (severity_filter == "All" or h.get("severity") == severity_filter)]

    if st.session_state.blind_mode:
        # Blind mode hazard display
        if st.button("🎧 Hear Nearby Hazards", key="hear_hazards_blind"):
            if hazards:
                hazard_list = ". ".join([f"{h['hazard_type']} at {h['full_location']}" for h in hazards])
                announce(f"Nearby hazards include: {hazard_list}")
            else:
                announce("No recent hazards reported in your area")
    else:
        # Regular mode hazard display
        if hazards:
            for i, h in enumerate(hazards):
                timestamp_str = h["timestamp"][:19].replace("T", " ")
                hazard_type = h.get("hazard_type", "Unknown")
                severity = h.get("severity", "Unknown")
                
                with st.expander(f"🧯 {timestamp_str} | {hazard_type} - {severity}"):
                    st.markdown(f"""
                    <div style='border:2px solid {severity_colors.get(severity, "#888")}; 
                                background-color:{bg_colors.get(severity, "#f9f9f9")};
                                padding:10px; border-radius:6px;'>
                        <b>📍 Location:</b> {h.get('full_location', 'Unknown')}<br>
                        <b>📞 Contact:</b> {h.get('contact', 'N/A')}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("Get Help", key=f"help_{h['timestamp']}_{i}"):
                        handle_hazard_help_request(h)
        
        else:
            st.info("✅ No hazards reported in this time range.")
            if st.session_state._accessibility_mode:
                announce("No hazards reported in this time range")

    # Map button (only shown in regular mode)
    if not st.session_state.blind_mode:
        st.markdown("---")
        st.subheader("🗺️ Explore Alerts on Map")
        if st.button("Show Alert Map", key="show_alert_map"):
            st.session_state.show_map_mode = True
            st.rerun()
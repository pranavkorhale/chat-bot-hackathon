from services.geolocation import reverse_geocode
from services.hazard_detection import classify_hazard_type
from services.speech import speak_async
from database.process_hazard import save_hazard_if_needed
import streamlit as st

# === Automatic Hazard Handling ===
def handle_auto_hazard(user_input):
    # Initialize accessibility_mode if it doesn't exist
    if 'accessibility_mode' not in st.session_state:
        st.session_state.accessibility_mode = False
    
    with st.spinner("🚨 Automatically processing hazard report..."):
        lat = 39.7684
        lon = -86.1581
        reverse_info = reverse_geocode(lat, lon)
        
        hazard_data = classify_hazard_type(user_input)
        
        hazard_record = {
            "description": f"**{hazard_data['hazard_type']} | {hazard_data['severity']}**\n\n{hazard_data['title']}\n\n{hazard_data['details']}\n\nLocation: Auto-detected downtown Indianapolis",
            "lat": lat,
            "lon": lon,
            "hazard_type": hazard_data["hazard_type"],
            "severity": hazard_data["severity"],
            "contact": "Auto-detected",
            "city": reverse_info.get("city", "Indianapolis"),
            "suburb": reverse_info.get("suburb", "Downtown"),
            "postcode": reverse_info.get("postcode", "46204"),
            "country": "United States",
            "full_location": reverse_info.get("display_name", "Downtown Indianapolis")
        }
        
        if save_hazard_if_needed(hazard_record):
            st.session_state.hazard_saved = True
            response = f"🚨 Automatic hazard report logged: {hazard_data['hazard_type']} at downtown Indianapolis. Severity: {hazard_data['severity']}. Authorities have been notified."
            st.session_state.response = response
            if st.session_state.accessibility_mode:
                speak_async(response)
        else:
            error_msg = "⚠️ Hazard detected but failed to automatically save report. Please try again or use manual reporting."
            st.session_state.response = error_msg
            if st.session_state.accessibility_mode:
                speak_async(error_msg)
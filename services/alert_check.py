import streamlit as st
from datetime import datetime, timedelta, timezone
from database.process_hazard import get_recent_hazards
from services.speech import speak_async



def get_filtered_hazards(time_range, hazard_type_filter, severity_filter):
    """Get hazards filtered by time range, type and severity"""
    time_mapping = {
        "Past 1 hour": timedelta(hours=1),
        "Past 2 hours": timedelta(hours=2),
        "Past 6 hours": timedelta(hours=6),
        "Past 24 hours": timedelta(hours=24)
    }
    
    hazards = get_recent_hazards(since=datetime.now(timezone.utc) - time_mapping[time_range])
    
    if hazard_type_filter != "All":
        hazards = [h for h in hazards if h.get("hazard_type") == hazard_type_filter]
    if severity_filter != "All":
        hazards = [h for h in hazards if h.get("severity") == severity_filter]
    
    return hazards

def format_alert_for_speech(hazard, index):
    """Convert hazard data into a speakable string"""
    timestamp = datetime.fromisoformat(hazard["timestamp"]).strftime("%I:%M %p")
    hazard_type = hazard.get("hazard_type", "Unknown hazard")
    location = hazard.get("suburb", hazard.get("city", "Unknown location"))
    severity = hazard.get("severity", "Unknown severity")
    
    return (
        f"Alert {index + 1}: {hazard_type} reported at {timestamp} in {location}. "
        f"Severity level: {severity}. "
        f"Description: {hazard.get('description', 'No details')[0:100]}"
    )

def announce_alerts(hazards, max_alerts=2):
    """Announce alerts through both UI and audio"""
    if not hazards:
        msg = "No alerts found in selected time frame"
        st.info(msg)
        if st.session_state.accessibility_mode and st.session_state.audio_available:
            speak_async(msg)
        return
    
    alert_count = min(len(hazards), max_alerts)
    st.success(f"Found {len(hazards)} alerts. Here are the first {alert_count}:")
    
    # Prepare combined message for audio
    audio_messages = [f"Found {len(hazards)} alerts."]
    
    for i in range(alert_count):
        alert_text = format_alert_for_speech(hazards[i], i)
        st.info(alert_text)
        audio_messages.append(alert_text)
    
    # Speak all alerts in one go
    if st.session_state.accessibility_mode and st.session_state.audio_available:
        speak_async(" ".join(audio_messages))
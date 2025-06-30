
from services.hazard_detection import is_actual_hazard
from services.speech import speak_async
from services.auto_hazard_handler import handle_auto_hazard
from backend.query_rag import get_response
import streamlit as st

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
            st.session_state.awaiting_location = is_hazard and not st.session_state.auto_hazard_mode
            st.session_state.hazard_saved = False
            st.session_state.reverse_info = None
            st.session_state.lat = None
            st.session_state.lon = None
            st.session_state.location_response = None
            st.session_state.last_input = user_input

            if st.session_state.accessibility_mode:
                speak_async(rough_response)

            if is_hazard and st.session_state.auto_hazard_mode:
                handle_auto_hazard(user_input)

    st.session_state.input_text = ""


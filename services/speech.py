# services/speech.py

import threading
from services.accessibility_utils import speak_text
import streamlit as st
# === Speak in background ===
def speak_async(text):
    """Safe async speech function"""
    def run():
        if text:
            try:
                st.session_state.is_speaking = True
                speak_text(text)
            except Exception as e:
                print(f"Audio error: {e}")
                if st.session_state.accessibility_mode:
                    st.error(f"Audio playback failed: {str(e)}")
            finally:
                st.session_state.is_speaking = False
    
    if text and st.session_state.get("_accessibility_mode", False):
        threading.Thread(target=run, daemon=True).start()


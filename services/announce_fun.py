import streamlit as st
import threading
from pygame import mixer
from services.accessibility_utils import speak_text


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

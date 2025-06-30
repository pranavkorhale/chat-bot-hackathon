from gtts import gTTS
import tempfile
import os
import speech_recognition as sr
import time
import streamlit as st
import threading

# Try to import and initialize pygame mixer safely
AUDIO_AVAILABLE = False
try:
    from pygame import mixer
    mixer.init()
    AUDIO_AVAILABLE = True
except Exception as e:
    print(f"Audio not available: {e}")

def speak_text(text):
    """Convert text to speech and play it using pygame mixer"""
    if not AUDIO_AVAILABLE:
        print(f"[AUDIO DISABLED] Would have spoken: {text}")
        return

    try:
        if not text or not isinstance(text, str):
            return
            
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts = gTTS(text=text, lang='en')
            tts.save(fp.name)
            temp_file = fp.name

        while mixer.music.get_busy():
            time.sleep(0.1)
        
        mixer.music.load(temp_file)
        mixer.music.play()

        def cleanup():
            while mixer.music.get_busy():
                time.sleep(0.1)
            try:
                os.remove(temp_file)
            except:
                pass
                
        threading.Thread(target=cleanup, daemon=True).start()
        
    except Exception as e:
        print(f"Speech synthesis failed: {str(e)}")

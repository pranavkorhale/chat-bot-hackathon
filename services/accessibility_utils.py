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
except Exception:
    # Avoid printing noisy logs in Streamlit UI
    AUDIO_AVAILABLE = False

def speak_text(text):
    """Convert text to speech and play it using pygame mixer (if available)."""
    if not AUDIO_AVAILABLE:
        # Optionally log to a file or suppress
        return

    try:
        if not text or not isinstance(text, str):
            return

        # Save the speech to a temporary mp3 file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            gTTS(text=text, lang='en').save(fp.name)
            temp_file = fp.name

        # Wait if audio is already playing
        while mixer.music.get_busy():
            time.sleep(0.1)

        mixer.music.load(temp_file)
        mixer.music.play()

        # Clean up the file after playback finishes
        def cleanup():
            while mixer.music.get_busy():
                time.sleep(0.1)
            try:
                os.remove(temp_file)
            except:
                pass

        threading.Thread(target=cleanup, daemon=True).start()

    except Exception as e:
        # Optionally log error silently
        pass


def record_and_transcribe():
    """Record audio from mic and transcribe using Google Speech Recognition."""
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            st.write("🎙️ Listening... (timeout in 5 sec)")
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=5)
            return recognizer.recognize_google(audio)
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except Exception:
        return None

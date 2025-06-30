import os
import sys
import tempfile
import time
import threading
import streamlit as st
import speech_recognition as sr
from gtts import gTTS

# === Silence audio system error popup (e.g., 'dsp: No such audio device') ===
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.stderr = open(os.devnull, 'w')
try:
    from pygame import mixer
    mixer.init()
    AUDIO_AVAILABLE = True
except Exception:
    AUDIO_AVAILABLE = False
finally:
    sys.stderr = sys.__stderr__  # Restore stderr output


def speak_text(text):
    """Convert text to speech and play it using pygame mixer (if available)."""
    if not AUDIO_AVAILABLE:
        return  # Audio not available; skip speech

    try:
        if not text or not isinstance(text, str):
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            gTTS(text=text, lang='en').save(fp.name)
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
            except Exception:
                pass

        threading.Thread(target=cleanup, daemon=True).start()

    except Exception:
        pass  # Fail silently


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

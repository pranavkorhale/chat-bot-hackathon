import os
import tempfile
import time
import threading
import asyncio
import streamlit as st
import speech_recognition as sr
import edge_tts
from pygame import mixer
import platform
from typing import Optional

# === Constants ===
MIN_AUDIO_DURATION = 2  # Minimum seconds to play audio
MAX_AUDIO_DURATION = 15  # Maximum seconds to play audio

# === Audio System Initialization ===
def _initialize_audio_system() -> bool:
    """Initialize audio system with OS-specific settings"""
    try:
        current_os = platform.system().lower()
        
        # Driver priority by OS
        driver_preference = {
            'linux': ['pulseaudio', 'alsa', 'dummy'],
            'darwin': ['coreaudio', 'openal', 'dummy'],  # macOS
            'windows': ['directsound', 'wasapi', 'dummy']
        }.get(current_os, ['dummy'])
        
        # Initialize mixer with best available driver
        for driver in driver_preference:
            os.environ['SDL_AUDIODRIVER'] = driver
            try:
                if mixer.get_init():
                    mixer.quit()
                mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                st.toast(f"Audio initialized with driver: {driver}", icon="🔊")
                return True
            except Exception as e:
                st.warning(f"Driver {driver} failed: {str(e)}")
                continue
                
        return False
    except Exception as e:
        st.error(f"Audio system initialization failed: {str(e)}")
        return False

AUDIO_AVAILABLE = _initialize_audio_system()

# === Text-to-Speech Core ===
async def _generate_speech(text: str, output_path: str, voice: str = "en-US-AriaNeural") -> bool:
    """Generate speech audio file"""
    try:
        communicate = edge_tts.Communicate(text=text, voice=voice)
        await communicate.save(output_path)
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1024
    except Exception as e:
        st.error(f"Speech generation error: {str(e)}")
        return False

def speak_text(text: str, interrupt: bool = True) -> bool:
    """
    Speak text aloud (cross-platform)
    
    Args:
        text: Text to speak
        interrupt: Whether to stop current playback
        
    Returns:
        bool: True if playback started successfully
    """
    if not AUDIO_AVAILABLE or not text or not isinstance(text, str):
        return False

    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        # Generate speech
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if not loop.run_until_complete(_generate_speech(text, temp_path)):
                return False
        finally:
            loop.close()

        # Handle playback
        if interrupt and mixer.music.get_busy():
            mixer.music.stop()
            time.sleep(0.2)

        mixer.music.load(temp_path)
        mixer.music.play()

        # Calculate reasonable playback duration
        word_count = len(text.split())
        playback_duration = min(MAX_AUDIO_DURATION, 
                               max(MIN_AUDIO_DURATION, word_count * 0.45))

        # Background cleanup
        def _cleanup():
            start_time = time.time()
            while (mixer.music.get_busy() and 
                   (time.time() - start_time < playback_duration)):
                time.sleep(0.1)
            try:
                os.remove(temp_path)
            except:
                pass

        threading.Thread(target=_cleanup, daemon=True).start()
        return True

    except Exception as e:
        st.error(f"Playback failed: {str(e)}")
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
        return False

# === Speech Recognition ===
def record_and_transcribe(timeout: int = 5, phrase_limit: int = 5) -> Optional[str]:
    """
    Record audio and transcribe to text
    
    Args:
        timeout: Seconds to wait for speech
        phrase_limit: Maximum duration of speech
        
    Returns:
        str: Transcribed text or None if failed
    """
    recognizer = sr.Recognizer()
    
    # OS-specific microphone settings
    os_settings = {
        'linux': {'energy_threshold': 5000, 'calibration_duration': 1.5},
        'darwin': {'energy_threshold': 4000, 'calibration_duration': 1.0}  # macOS
    }.get(platform.system().lower(), 
          {'energy_threshold': 4000, 'calibration_duration': 1.0})
    
    recognizer.energy_threshold = os_settings['energy_threshold']
    recognizer.dynamic_energy_threshold = True
    
    try:
        with sr.Microphone() as source:
            st.session_state.is_listening = True
            with st.spinner("🎤 Listening..."):
                # Calibrate and record
                recognizer.adjust_for_ambient_noise(
                    source, 
                    duration=os_settings['calibration_duration']
                )
                audio = recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_limit
                )
                
            st.session_state.is_listening = False
            return recognizer.recognize_google(audio)
            
    except sr.WaitTimeoutError:
        st.warning("No speech detected")
        return None
    except sr.UnknownValueError:
        st.warning("Could not understand audio")
        return None
    except Exception as e:
        st.error(f"Recording error: {str(e)}")
        return None
    finally:
        st.session_state.is_listening = False

# === Debug Utilities ===
def audio_debug_panel():
    """Audio system debug panel for troubleshooting"""
    with st.sidebar.expander("🔧 Audio Diagnostics", expanded=False):
        st.write(f"**OS:** {platform.system()} {platform.release()}")
        st.write(f"**Audio System:** {'✅ Ready' if AUDIO_AVAILABLE else '❌ Failed'}")
        
        if st.button("Test Playback"):
            if speak_text("This is an audio system test"):
                st.success("Playback successful!")
            else:
                st.error("Playback failed")
                
        if st.button("Test Microphone"):
            text = record_and_transcribe()
            st.write(f"**Heard:** {text if text else 'Nothing'}")

        if st.button("List Audio Devices"):
            try:
                import sounddevice as sd
                devices = sd.query_devices()
                st.write("**Audio Devices:**", devices)
            except Exception as e:
                st.error(f"Could not list devices: {str(e)}")

# Initialize session state
if 'is_listening' not in st.session_state:
    st.session_state.is_listening = False
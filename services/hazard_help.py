import streamlit as st
from backend.query_rag import get_llm
from services.announce_fun import announce

def handle_hazard_help_request(hazard):
    """Handles help requests for specific hazards with voice support"""
    try:
        llm = get_llm()
        help_prompt = f"""
        A person needs help regarding this hazard:
        Type: {hazard.get('hazard_type', 'Unknown')}
        Severity: {hazard.get('severity', 'Unknown')}
        Location: {hazard.get('full_location', 'Unknown location')}
        Contact: {hazard.get('contact', 'Not provided')}

        Provide helpful and actionable advice as SafeIndyBot.
        Include emergency contacts if appropriate.
        """
        response = llm.complete(prompt=help_prompt)
        help_response = response.text.strip()
        
        # Display and announce the response
        st.markdown(
            f'<div class="chat-box"><b>🤖 SafeIndyBot Help:</b><br>{help_response}</div>',
            unsafe_allow_html=True
        )
        
        if st.session_state._accessibility_mode:
            announce(help_response)
            
    except Exception as e:
        error_msg = f"Failed to get help: {str(e)}"
        st.error(error_msg)
        if st.session_state._accessibility_mode:
            announce(error_msg)
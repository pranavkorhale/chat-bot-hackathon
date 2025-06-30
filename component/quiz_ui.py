
import streamlit as st
from datetime import datetime
from services.quiz_generator import generate_quiz_batch



def show_quiz_ui():
    st.subheader("🧠 Test Your Knowledge")

    if st.button("Take Quiz"):
        st.session_state.quiz_data = generate_quiz_batch()
        if not st.session_state.quiz_data:
            st.error("❌ Failed to load quiz questions. Please try again.")
            return
        st.session_state.current_question = 0
        st.session_state.score = 0
        st.session_state.quiz_done = False
        st.session_state.show_quiz = True
        st.rerun()

    if st.session_state.get("show_quiz", False):

        if st.session_state.get("quiz_done", False):
            score = st.session_state.score
            total = len(st.session_state.quiz_data)
            percentage = (score / total) * 100

            st.success(f"✅ Quiz complete! Your score: {score} / {total}")

            if percentage == 100:
                st.balloons()
                st.info("🎉 Perfect score! You're a safety expert!")
            elif percentage >= 80:
                st.success("👏 Great job! You really know your safety hazards.")
            elif percentage >= 50:
                st.warning("👍 Not bad! Review some hazards to improve.")
            else:
                st.error("📚 Consider reviewing hazard safety more. Stay safe!")

            # 🎓 Show certificate if score >= 9
            if score >= 9:
                st.markdown("### 🎓 Congratulations!")
                st.success("You scored 9 or more! You're eligible for a SafeIndy Safety Certificate.")

                cert_text = f"""Certificate of Completion
==========================
Awarded to: Safety Quiz Participant
Score: {score}/{total}
Date: {datetime.now().strftime('%B %d, %Y')}
Presented by: SafeIndy Public Safety Program
"""

                st.download_button(
                    label="📄 Download Certificate",
                    data=cert_text,
                    file_name="safeindy_certificate.txt",
                    mime="text/plain"
                )

            if st.button("🔄 Take Again"):
                st.session_state.quiz_data = generate_quiz_batch()
                st.session_state.current_question = 0
                st.session_state.score = 0
                st.session_state.quiz_done = False
                st.rerun()
            return

        quiz_data = st.session_state.get("quiz_data", [])
        q_index = st.session_state.get("current_question", 0)

        if not quiz_data:
            st.error("❌ Quiz questions not loaded. Please try again.")
            return

        if q_index < len(quiz_data):
            q_data = quiz_data[q_index]
            st.markdown(f"**Q{q_index + 1}: {q_data['question']}**")

            user_choice = st.radio(
                "Choose your answer:",
                q_data["options"],
                key=f"quiz_q{q_index}",
                label_visibility="collapsed"
            )

            if st.button("Submit Answer"):
                selected_index = q_data["options"].index(user_choice)
                if selected_index == q_data["answer"]:
                    st.session_state.score += 1
                    st.success("✅ Correct!")
                else:
                    correct_text = q_data["options"][q_data["answer"]]
                    st.error(f"❌ Incorrect. Correct answer was: {correct_text}")

                st.session_state.current_question += 1

                if st.session_state.current_question >= len(quiz_data):
                    st.session_state.quiz_done = True

                st.rerun()

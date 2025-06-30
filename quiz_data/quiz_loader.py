import json
import os

def load_quiz_questions(path="quiz_data/quiz_questions.json", n=10):
    """
    Load quiz questions from a JSON file and return n random questions.

    Each question should have the following format:
    {
        "question": "What is the best action during a fire?",
        "options": ["Run and scream", "Call 911 and evacuate", "Hide under the bed"],
        "answer": 1
    }
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Quiz file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        all_questions = json.load(f)

    if len(all_questions) < n:
        return all_questions
    else:
        import random
        return random.sample(all_questions, n)

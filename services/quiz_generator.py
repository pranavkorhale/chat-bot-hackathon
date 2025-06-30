
import random
from quiz_data.quiz_loader import load_quiz_questions

def generate_quiz_batch(n=10):
    all_questions = load_quiz_questions()
    return random.sample(all_questions, min(n, len(all_questions)))

import csv
import random
from pathlib import Path


QUESTIONS_FILE = Path(__file__).with_name("questions.csv")
CHOICES = ("A", "B", "C", "D")
DIFFICULTIES = ("Easy", "Medium", "Hard")
QUESTIONS_PER_GAME = 5


def load_questions(file_path=QUESTIONS_FILE):
    """Load and validate trivia questions from a CSV file."""
    with file_path.open(newline="", encoding="utf-8") as questions_file:
        questions = list(csv.DictReader(questions_file))

    required_fields = {
        "category",
        "question",
        "A",
        "B",
        "C",
        "D",
        "answer",
        "explanation",
        "difficulty",
    }
    if not questions or not required_fields.issubset(questions[0]):
        raise ValueError("The question file is empty or has missing columns.")

    for question in questions:
        if question["answer"].strip().upper() not in CHOICES:
            raise ValueError("Each question's answer must be A, B, C, or D.")
        if question["difficulty"].strip().title() not in DIFFICULTIES:
            raise ValueError("Each question must have an Easy, Medium, or Hard difficulty.")
        if any(not question[field].strip() for field in required_fields):
            raise ValueError("Question fields cannot be empty.")

    return questions


def calculate_score(correct_answers, total_questions):
    """Return the percentage score, or zero when there are no questions."""
    if total_questions == 0:
        return 0
    return round(correct_answers / total_questions * 100)


def choose_difficulty():
    """Ask the player to choose a question difficulty."""
    print("Choose a difficulty:")
    for difficulty_number, difficulty in enumerate(DIFFICULTIES, start=1):
        print(f"  {difficulty_number}. {difficulty}")

    while True:
        selection = input("Enter 1, 2, or 3: ").strip()
        if selection in {"1", "2", "3"}:
            return DIFFICULTIES[int(selection) - 1]
        print("Please enter 1, 2, or 3.")


def ask_question(question, question_number, total_questions):
    """Display one question and return whether the player's answer is correct."""
    print(f"\nQuestion {question_number} of {total_questions} [{question['category']}]")
    print(question["question"])
    for choice in CHOICES:
        print(f"  {choice}. {question[choice]}")

    answer = input("Your answer (A-D): ").strip().upper()
    while answer not in CHOICES:
        answer = input("Please enter A, B, C, or D: ").strip().upper()

    correct_answer = question["answer"].strip().upper()
    is_correct = answer == correct_answer
    if is_correct:
        print("Correct!")
    else:
        print(f"Not quite. The correct answer is {correct_answer}.")
    print(question["explanation"])
    return is_correct


def play_game(questions):
    """Run one round of history trivia and display the final score."""
    if len(questions) < QUESTIONS_PER_GAME:
        raise ValueError(
            f"Add at least {QUESTIONS_PER_GAME} questions at this difficulty to play."
        )

    selected_questions = random.sample(questions, QUESTIONS_PER_GAME)
    correct_answers = 0
    for question_number, question in enumerate(selected_questions, start=1):
        if ask_question(question, question_number, QUESTIONS_PER_GAME):
            correct_answers += 1

    score = calculate_score(correct_answers, QUESTIONS_PER_GAME)
    print(f"\nYour score: {correct_answers}/{QUESTIONS_PER_GAME} ({score}%)")


def main():
    try:
        questions = load_questions()
        selected_difficulty = choose_difficulty()
        selected_questions = [
            question
            for question in questions
            if question["difficulty"].strip().title() == selected_difficulty
        ]
        play_game(selected_questions)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Could not start the history trivia game: {error}") from error


if __name__ == "__main__":
    main()

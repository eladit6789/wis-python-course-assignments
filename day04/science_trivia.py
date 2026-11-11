import csv
import random
from pathlib import Path


QUESTIONS_FILE = Path(__file__).with_name("questions.csv")
CHOICES = ("A", "B", "C", "D")
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
    }
    if not questions or not required_fields.issubset(questions[0]):
        raise ValueError("The question file is empty or has missing columns.")

    for question in questions:
        if question["answer"].strip().upper() not in CHOICES:
            raise ValueError("Each question's answer must be A, B, C, or D.")
        if any(not question[field].strip() for field in required_fields):
            raise ValueError("Question fields cannot be empty.")

    return questions


def calculate_score(correct_answers, total_questions):
    """Return the percentage score, or zero when there are no questions."""
    if total_questions == 0:
        return 0
    return round(correct_answers / total_questions * 100)


def choose_categories(questions):
    """Ask which question categories to include in a round."""
    categories = list(dict.fromkeys(question["category"] for question in questions))
    print("Choose the science areas to include:")
    for category_number, category in enumerate(categories, start=1):
        print(f"  {category_number}. {category}")

    while True:
        selection = input("Enter numbers separated by commas, or A for all: ").strip()
        if selection.casefold() in {"a", "all"}:
            return set(categories)

        selected_numbers = [number.strip() for number in selection.split(",")]
        if selected_numbers and all(
            number.isdigit() and 1 <= int(number) <= len(categories)
            for number in selected_numbers
        ):
            return {categories[int(number) - 1] for number in selected_numbers}

        print("Choose at least one listed number, or enter A for all.")


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
    """Run one round of trivia and display the final score."""
    if len(questions) < QUESTIONS_PER_GAME:
        raise ValueError(f"Add at least {QUESTIONS_PER_GAME} questions to play.")

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
        selected_categories = choose_categories(questions)
        selected_questions = [
            question
            for question in questions
            if question["category"] in selected_categories
        ]
        play_game(selected_questions)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Could not start the trivia game: {error}") from error


if __name__ == "__main__":
    main()
import os
import random
import secrets

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from science_trivia import CHOICES, QUESTIONS_PER_GAME, calculate_score, load_questions
from training.dna_composition import calculate_percentages


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
QUESTIONS = load_questions()
CATEGORIES = sorted({question["category"] for question in QUESTIONS})


def render_setup(error=None, status=200):
    return (
        render_template(
            "index.html",
            categories=CATEGORIES,
            question_count=len(QUESTIONS),
            error=error,
        ),
        status,
    )


def get_game_questions():
    indices = session.get("question_indices")
    if (
        not isinstance(indices, list)
        or len(indices) != QUESTIONS_PER_GAME
        or any(type(index) is not int or not 0 <= index < len(QUESTIONS) for index in indices)
    ):
        return None
    return [QUESTIONS[index] for index in indices]


@app.get("/")
def index():
    return render_setup()


@app.route("/dna", methods=["GET", "POST"])
def dna_calculator():
    sequence = ""
    percentages = None
    error = None

    if request.method == "POST":
        sequence = request.form.get("sequence", "")
        try:
            percentages = calculate_percentages(sequence)
        except ValueError as exc:
            error = str(exc)

    return render_template(
        "dna.html",
        sequence=sequence,
        percentages=percentages,
        error=error,
    )


@app.post("/start")
def start_game():
    selected_categories = set(request.form.getlist("categories"))
    if not selected_categories or not selected_categories.issubset(CATEGORIES):
        return render_setup("Choose at least one listed science area.", 400)

    eligible_indices = [
        index
        for index, question in enumerate(QUESTIONS)
        if question["category"] in selected_categories
    ]
    if len(eligible_indices) < QUESTIONS_PER_GAME:
        return render_setup(
            f"Choose areas with at least {QUESTIONS_PER_GAME} questions to start a round.",
            400,
        )

    session.clear()
    session["question_indices"] = random.sample(eligible_indices, QUESTIONS_PER_GAME)
    session["question_index"] = 0
    session["answers"] = []
    return redirect(url_for("play"))


@app.get("/play")
def play():
    game_questions = get_game_questions()
    question_index = session.get("question_index")
    if (
        game_questions is None
        or type(question_index) is not int
        or not 0 <= question_index < QUESTIONS_PER_GAME
    ):
        return redirect(url_for("index"))

    question = game_questions[question_index]
    return render_template(
        "question.html",
        question={
            "category": question["category"],
            "question": question["question"],
            "choices": [(choice, question[choice]) for choice in CHOICES],
        },
        question_number=question_index + 1,
        total_questions=QUESTIONS_PER_GAME,
    )


@app.post("/answer")
def submit_answer():
    game_questions = get_game_questions()
    question_index = session.get("question_index")
    if (
        game_questions is None
        or type(question_index) is not int
        or not 0 <= question_index < QUESTIONS_PER_GAME
    ):
        return redirect(url_for("index"))

    if request.form.get("question_index") != str(question_index):
        abort(400, description="This answer was already submitted or is out of date.")

    answer = request.form.get("answer", "").strip().upper()
    if answer not in CHOICES:
        flash("Choose A, B, C, or D before continuing.", "error")
        return redirect(url_for("play"))

    question = game_questions[question_index]
    answers = session.get("answers", [])
    answers.append(
        {
            "question_index": session["question_indices"][question_index],
            "answer": answer,
            "correct": answer == question["answer"].strip().upper(),
        }
    )
    session["answers"] = answers
    session["question_index"] = question_index + 1

    if session["question_index"] == QUESTIONS_PER_GAME:
        return redirect(url_for("results"))
    return redirect(url_for("play"))


@app.get("/results")
def results():
    game_questions = get_game_questions()
    answers = session.get("answers")
    if (
        game_questions is None
        or not isinstance(answers, list)
        or len(answers) != QUESTIONS_PER_GAME
    ):
        return redirect(url_for("index"))

    correct_answers = sum(answer["correct"] for answer in answers)
    score = calculate_score(correct_answers, QUESTIONS_PER_GAME)
    review = []
    for question, answer in zip(game_questions, answers):
        review.append(
            {
                "question": question["question"],
                "selected": question[answer["answer"]],
                "correct_answer": question[question["answer"].strip().upper()],
                "explanation": question["explanation"],
                "correct": answer["correct"],
            }
        )

    return render_template(
        "results.html",
        correct_answers=correct_answers,
        total_questions=QUESTIONS_PER_GAME,
        score=score,
        review=review,
    )


@app.get("/new-game")
def new_game():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=False)

# Day 04 — Science Showdown Web App

This folder preserves the complete day 3 assignment, including its original command-line game, browser game, question bank, and training exercise. The `app.py` quiz app reuses the original Python question loader, answer choices, round length, and score calculation. The DNA calculator runs as a separate Flask app.

The original day 3 instructions are preserved in [`README-day03.md`](README-day03.md).

## Run the web app

From the repository root, install the day 4 dependency and start Flask:

```text
python -m pip install -r day04/requirements.txt
python day04/app.py
```

Open <http://127.0.0.1:5000> in a browser. Choose either the science trivia or the Weizmann Institute history quiz. The science quiz lets you select one or more science areas; both quizzes ask five questions and show your score and answer review when the round is complete. The history quiz uses `weizmann_history_trivia/questions.csv`.

## Run the separate DNA calculator app

In another terminal, from the repository root, run:

```text
python day04/dna_app.py
```

Open <http://127.0.0.1:5001> in a browser. Enter a sequence containing A, C, G, and T to see individual nucleotide percentages and combined CG/AT percentages. This app reuses the calculation function from `training/dna_composition.py`. It runs independently of the quiz app; both apps can be running at the same time.

To run with a stable Flask session key, set `FLASK_SECRET_KEY` in your environment before starting the app. Without it, the app generates a temporary key each time it starts.

## Run the preserved command-line game

From the repository root, run:

```text
python day04/science_trivia.py
```

It uses the copied `questions.csv` file and remains separate from the Flask interface.

## Run the web app tests

```text
python -m unittest discover -s day04 -p "test_*.py"
```

## Files

- `app.py` — Flask routes and web game flow.
- `dna_app.py` — separate Flask app for the DNA calculator (port 5001).
- `templates/` and `static/` — server-rendered game, calculator pages, and styles.
- `science_trivia.py` — preserved command-line implementation and shared business logic.
- `questions.csv` — copied question bank used by both Python game interfaces.
- `weizmann_history_trivia/questions.csv` — question bank for the Institute history quiz in the Flask app.
- `test_app.py` and `test_dna_app.py` — tests for the quiz and calculator apps.
- `science_trivia.html`, `science_trivia.js`, and `science_trivia.css` — preserved day 3 browser version.
- `README-day03.md` — the original day 3 instructions.
- `weizmann_history_trivia/` and `training/` — preserved day 3 project and practice files.

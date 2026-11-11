# Day 04 — Science Showdown Web App

This folder preserves the complete day 3 assignment, including its original command-line game, browser game, question bank, and training exercise. The new `app.py` adds a Flask web app that reuses the original Python question loader, answer choices, round length, and score calculation.

The original day 3 instructions are preserved in [`README-day03.md`](README-day03.md).

## Run the web app

From the repository root, install the day 4 dependency and start Flask:

```text
python -m pip install -r day04/requirements.txt
python day04/app.py
```

Open <http://127.0.0.1:5000> in a browser. Select one or more science areas and answer five questions. The score and answer review are calculated and displayed when the round is complete.

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
- `templates/` and `static/` — server-rendered pages and styles.
- `science_trivia.py` — preserved command-line implementation and shared business logic.
- `questions.csv` — copied question bank used by both Python game interfaces.
- `test_app.py` — tests for game flow and input validation.
- `science_trivia.html`, `science_trivia.js`, and `science_trivia.css` — preserved day 3 browser version.
- `README-day03.md` — the original day 3 instructions.
- `weizmann_history_trivia/` and `training/` — preserved day 3 project and practice files.

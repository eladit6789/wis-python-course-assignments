# Day 03 - Basic Science Trivia

## What the program does

`science_trivia.html` is a browser game about biology, chemistry, physics, and
Earth science. It chooses five questions at random from an 80-question pool in `questions.csv`,
checks the player's answers, explains each answer, and displays the final
score. Players can choose one or more science areas before starting. All four
areas are selected by default. The command-line version offers the same choice
by number or lets players include all areas.

The questions are stored separately from the program, so the question bank
can be expanded by adding rows to the CSV file. Each question includes four
choices, the correct answer, and a short explanation.

## How to run

To play the browser game, start a local web server from the `day03` folder:

```text
python -m http.server 8000
```

Then open `http://localhost:8000/science_trivia.html` in a browser. Python 3
is required to serve the files; no extra packages are needed.

To run the command-line version from the repository folder:

```text
python day03\science_trivia.py
```

Choose one or more science area numbers separated by commas, or enter `A` to
include all areas.

## Files

- `science_trivia.py` - loads the questions, runs the quiz, and calculates the
  score.
- `science_trivia.html`, `science_trivia.css`, and `science_trivia.js` - the
  browser game interface and gameplay.
- `questions.csv` - the science trivia question bank.
- `training/` - a separate folder for the DNA-composition practice exercise
  and its sample sequence.

To run the training exercise, use:

```text
python day03\training\dna_composition.py
```

## AI prompts

Prompts used with AI in VS Code:

- "Help me make a beginner-friendly command-line trivia game about basic
  science. Store the questions and answers in a CSV file."
- "Help me organize the game into functions for loading questions, asking
  questions, and calculating the score."
- "Review the game for invalid input and explain the correct answer after each
  question."
- "Write a README explaining how to run the game and list the AI prompts used."
- "Refresh the browser game's design for desktop and mobile and expand the basic science question pool."
- "Let players choose which science categories to include in a trivia round."

I reviewed the questions and tried the program, including invalid answer input.

## GitHub issue

Create the assignment issue on GitHub: [Add a basic science trivia game for Day 03](https://github.com/eladit6789/wis-python-course-assignments/issues/new?title=Day%2003%3A%20Basic%20Science%20Trivia)

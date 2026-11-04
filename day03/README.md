# Day 03 — Basic Science Trivia

This folder contains **two ways to play the same science trivia game**: a browser game and a command-line game. Both use the questions in `questions.csv`. There is also a separate DNA-composition practice exercise in `training/`.

## The trivia game

The game covers biology, chemistry, physics, and Earth science. Each round asks five randomly selected questions from the question bank. Choose which science areas to include before the round starts; all four are selected by default. After each answer, the game shows whether it was correct and provides an explanation.

### Option 1: Play in a browser

**Play the published game:** [Science Showdown](https://eladit6789.github.io/wis-python-course-assignments/day03/science_trivia.html). Open the link in a modern browser. You do not need to install Python or run a local server to play the published version.

**Run the browser game from your own copy:** Because the game loads `questions.csv`, open it through a local web server rather than opening the HTML file directly.

1. Install Python 3 if it is not already installed.
2. Open a terminal in the repository's `day03` folder. For example, from the repository root, run:

   ```text
   cd day03
   ```

3. Start the server:

   ```text
   python -m http.server 8000
   ```

   If `python` is not recognized, try `py -3 -m http.server 8000` on Windows or `python3 -m http.server 8000` on macOS/Linux.

4. Visit <http://localhost:8000/science_trivia.html> in your browser.
5. When you are finished, stop the server with `Ctrl+C` in the terminal.

The local browser game is implemented with HTML, CSS, and JavaScript. Python is only used to serve the local files; no extra packages are needed.

### Option 2: Play in the command line

This version runs in a terminal and is implemented in Python. From the repository root, run:

```text
python day03/science_trivia.py
```

If needed, replace `python` with `py -3` on Windows or `python3` on macOS/Linux. Python 3 is required; no additional packages are needed.

When prompted, enter one or more science-area numbers separated by commas, or enter `A` to include all areas. Then answer each question by entering `A`, `B`, `C`, or `D`.

## Separate exercise: DNA composition

`training/dna_composition.py` is a separate practice exercise; it is not another way to play trivia. It reads the example sequence from `sample_dna.txt` and prints the percentages of each DNA base, along with the combined CG and AT percentages.

From the repository root, run:

```text
python day03/training/dna_composition.py
```

As with the trivia game, use `py -3` or `python3` instead of `python` if that is the Python 3 command on your system.

## Files

- `science_trivia.html`, `science_trivia.css`, and `science_trivia.js` — the browser version of Science Showdown.
- `science_trivia.py` — the command-line version of the trivia game.
- `questions.csv` — the question bank used by both trivia versions.
- `training/dna_composition.py` — the separate DNA-composition exercise.
- `training/sample_dna.txt` — the sample sequence used by the DNA exercise.

## AI prompts

Prompts used with AI in VS Code:

- "Help me make a beginner-friendly command-line trivia game about basic science. Store the questions and answers in a CSV file."
- "Help me organize the game into functions for loading questions, asking questions, and calculating the score."
- "Review the game for invalid input and explain the correct answer after each question."
- "Write a README explaining how to run the game and list the AI prompts used."
- "Refresh the browser game's design for desktop and mobile and expand the basic science question pool."
- "Let players choose which science categories to include in a trivia round."

I reviewed the questions and tried the program, including invalid answer input.

## GitHub issue

[Add a basic science trivia game for Day 03](https://github.com/eladit6789/wis-python-course-assignments/issues/new?title=Day%2003%3A%20Basic%20Science%20Trivia)

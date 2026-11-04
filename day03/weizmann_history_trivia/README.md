# Weizmann Institute History Quiz

This folder contains a browser game and a command-line game about the history of the Weizmann Institute of Science. Both versions use `questions.csv`. Each round has five questions, and players can choose Easy, Medium, or Hard.

The questions cover the Institute's founding as the Daniel Sieff Research Institute in Rehovot in 1934, Chaim Weizmann, the 1949 renaming, and early research milestones such as WEIZAC.

## Play in a browser

The browser game loads its question bank from a CSV file, so run it through a local web server:

1. Open a terminal in this folder.
2. Start the server:

   ```text
   python -m http.server 8000
   ```

   On Windows, use `py -3 -m http.server 8000` if `python` is not recognized. On macOS or Linux, use `python3 -m http.server 8000` if needed.
3. Visit <http://localhost:8000/history_trivia.html>.
4. Stop the server with `Ctrl+C` when you are finished.

Choose a difficulty, answer with the buttons or the A-D keys, and use **Next** to continue. Correct answers are worth 20 points, with a 5-point bonus for each correct answer after the first in a consecutive streak. The browser saves your best score in local storage and reviews missed questions at the end of a round.

## Play in the command line

From the repository root, run:

```text
python day03/weizmann_history_trivia/history_trivia.py
```

Use `py -3` on Windows or `python3` on macOS or Linux if that is your Python 3 command. Choose a difficulty and answer each question with A, B, C, or D. No extra packages are required.

## Files

- `history_trivia.html`, `history_trivia.css`, and `history_trivia.js` — the browser game.
- `history_trivia.py` — the command-line game.
- `questions.csv` — the shared question bank.

## Sources

- [Weizmann Institute of Science — Wikipedia history overview](https://en.wikipedia.org/wiki/Weizmann_Institute_of_Science#History), including the founding, naming, Chaim Weizmann, and WEIZAC milestones.

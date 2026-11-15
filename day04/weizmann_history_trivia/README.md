# Weizmann Institute History Quiz

This folder contains a browser game and a command-line game about the history of the Weizmann Institute of Science. Both versions use `questions.csv`. Each round has five questions, and players can choose Easy, Medium, or Hard.

The 50-question bank covers the Institute's founding and early leadership, Chaim Weizmann, WEIZAC and the beginnings of computing in Israel, and later research and education milestones.

## Play in a browser

**Play the published game:** [Weizmann Institute History Quiz](https://eladit6789.github.io/wis-python-course-assignments/day03/weizmann_history_trivia/history_trivia.html). Open the link in a modern browser; no Python installation or local server is needed.

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

- [Weizmann Institute of Science — history overview](https://en.wikipedia.org/wiki/Weizmann_Institute_of_Science#History), including its founding, renaming, and later milestones.
- [WEIZAC](https://en.wikipedia.org/wiki/WEIZAC), including its development, scientific uses, and operating history; the article cites Institute and IEEE history sources.
- [Weizmann Institute — Computer Studies](https://wis-wander.weizmann.ac.il/content/computer-studies#%20The%20first%20computers), on the Institute's early computing history.
- [American Committee for the Weizmann Institute — Remembering WEIZAC](https://www.weizmann-usa.org/news-media/in-the-news/remembering-weizac-the-beginning-of-computing-in-israel/).

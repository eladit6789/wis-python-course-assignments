import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import science_trivia


CSV_FIELDS = (
    "category",
    "question",
    "A",
    "B",
    "C",
    "D",
    "answer",
    "explanation",
)


def make_question(number=1, category="Biology", answer="A"):
    return {
        "category": category,
        "question": f"Question {number}?",
        "A": "Choice A",
        "B": "Choice B",
        "C": "Choice C",
        "D": "Choice D",
        "answer": answer,
        "explanation": f"Explanation {number}.",
    }


class ScienceTriviaBusinessLogicTests(unittest.TestCase):
    def write_csv(self, directory, fieldnames, rows):
        path = Path(directory) / "questions.csv"
        with path.open("w", newline="", encoding="utf-8") as questions_file:
            writer = csv.DictWriter(questions_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_bundled_question_bank_is_valid_and_playable(self):
        questions = science_trivia.load_questions()

        self.assertGreaterEqual(
            len(questions), science_trivia.QUESTIONS_PER_GAME
        )
        self.assertTrue(
            all(question["answer"] in science_trivia.CHOICES
                for question in questions)
        )

    def test_load_questions_rejects_missing_columns(self):
        fields = tuple(field for field in CSV_FIELDS if field != "D")
        row = {field: "value" for field in fields}

        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(directory, fields, [row])
            with self.assertRaisesRegex(
                ValueError, "empty or has missing columns"
            ):
                science_trivia.load_questions(path)

    def test_load_questions_rejects_invalid_answers_and_blank_fields(self):
        invalid_answer = make_question(answer="E")
        blank_question = make_question()
        blank_question["question"] = ""

        with tempfile.TemporaryDirectory() as directory:
            invalid_path = self.write_csv(
                directory, CSV_FIELDS, [invalid_answer]
            )
            with self.assertRaisesRegex(ValueError, "answer must be A, B, C, or D"):
                science_trivia.load_questions(invalid_path)

            blank_path = self.write_csv(directory, CSV_FIELDS, [blank_question])
            with self.assertRaisesRegex(ValueError, "fields cannot be empty"):
                science_trivia.load_questions(blank_path)

    def test_load_questions_rejects_missing_cell_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.csv"
            path.write_text(
                "category,question,A,B,C,D,answer,explanation\n"
                "Biology,Question?,Choice A,Choice B,Choice C,Choice D,A\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "fields cannot be empty"):
                science_trivia.load_questions(path)

    def test_calculate_score_handles_full_partial_and_empty_rounds(self):
        self.assertEqual(science_trivia.calculate_score(5, 5), 100)
        self.assertEqual(science_trivia.calculate_score(2, 3), 67)
        self.assertEqual(science_trivia.calculate_score(0, 0), 0)

    def test_choose_categories_maps_numbers_and_retries_invalid_input(self):
        questions = [
            make_question(category="Biology"),
            make_question(category="Chemistry"),
            make_question(category="Biology"),
            make_question(category="Physics"),
        ]
        output = io.StringIO()

        with patch(
            "builtins.input", side_effect=["0", "3, 1"]
        ), redirect_stdout(output):
            selected = science_trivia.choose_categories(questions)

        self.assertEqual(selected, {"Biology", "Physics"})
        self.assertIn("Choose at least one listed number", output.getvalue())

    def test_choose_categories_accepts_all_case_insensitively(self):
        questions = [
            make_question(category="Biology"),
            make_question(category="Chemistry"),
        ]

        with patch("builtins.input", return_value=" all "):
            selected = science_trivia.choose_categories(questions)

        self.assertEqual(selected, {"Biology", "Chemistry"})

    def test_ask_question_retries_invalid_answer_and_normalizes_input(self):
        output = io.StringIO()
        with patch(
            "builtins.input", side_effect=["x", " b "]
        ) as input_mock, redirect_stdout(output):
            is_correct = science_trivia.ask_question(
                make_question(answer="B"), 1, 1
            )

        self.assertTrue(is_correct)
        self.assertEqual(input_mock.call_count, 2)
        self.assertIn(
            "Please enter A, B, C, or D",
            input_mock.call_args_list[1].args[0]
        )
        self.assertIn("Correct!", output.getvalue())
        self.assertIn("Explanation 1.", output.getvalue())

    def test_ask_question_reports_incorrect_answer(self):
        output = io.StringIO()
        with patch("builtins.input", return_value="D"), redirect_stdout(output):
            is_correct = science_trivia.ask_question(
                make_question(answer="A"), 1, 1
            )

        self.assertFalse(is_correct)
        self.assertIn("The correct answer is A", output.getvalue())

    def test_play_game_requires_five_questions(self):
        with self.assertRaisesRegex(ValueError, "at least 5 questions"):
            science_trivia.play_game([make_question()])

    def test_play_game_samples_five_questions_and_reports_score(self):
        questions = [
            make_question(number=number)
            for number in range(1, science_trivia.QUESTIONS_PER_GAME + 1)
        ]
        output = io.StringIO()
        answers = [True, False, True, False, False]

        with patch(
            "science_trivia.random.sample", return_value=questions
        ) as sample:
            with patch(
                "science_trivia.ask_question", side_effect=answers
            ) as ask:
                with redirect_stdout(output):
                    science_trivia.play_game(questions)

        sample.assert_called_once_with(
            questions, science_trivia.QUESTIONS_PER_GAME
        )
        self.assertEqual(ask.call_count, science_trivia.QUESTIONS_PER_GAME)
        self.assertIn("Your score: 2/5 (40%)", output.getvalue())


if __name__ == "__main__":
    unittest.main()

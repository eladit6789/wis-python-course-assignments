import unittest

import app as trivia_app


class TriviaWebAppTests(unittest.TestCase):
    def setUp(self):
        trivia_app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = trivia_app.app.test_client()

    def test_setup_lists_categories(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for category in trivia_app.CATEGORIES:
            self.assertIn(category.encode(), response.data)

    def test_round_uses_shared_question_bank_and_score_logic(self):
        response = self.client.post("/start", data={"categories": "Biology"})
        self.assertEqual(response.status_code, 302)

        with self.client.session_transaction() as game_session:
            indices = list(game_session["question_indices"])
        self.assertEqual(len(indices), trivia_app.QUESTIONS_PER_GAME)
        self.assertEqual(len(set(indices)), trivia_app.QUESTIONS_PER_GAME)
        self.assertTrue(
            all(trivia_app.QUESTIONS[index]["category"] == "Biology" for index in indices)
        )

        for question_number, question_index in enumerate(indices):
            page = self.client.get("/play")
            self.assertEqual(page.status_code, 200)
            self.assertIn(
                f"QUESTION {question_number + 1}".encode(),
                page.data,
            )
            response = self.client.post(
                "/answer",
                data={
                    "question_index": str(question_number),
                    "answer": trivia_app.QUESTIONS[question_index]["answer"],
                },
            )
            self.assertEqual(response.status_code, 302)

        results = self.client.get("/results")
        self.assertEqual(results.status_code, 200)
        self.assertIn(b"Your score:", results.data)
        self.assertIn(b"<span>100%</span>", results.data)
        self.assertIn(b"5 out of 5 correct", results.data)

    def test_start_rejects_empty_or_unknown_categories(self):
        for data in ({}, {"categories": "Unknown"}):
            with self.subTest(data=data):
                response = self.client.post("/start", data=data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(b"Choose at least one listed science area", response.data)

    def test_answer_rejects_stale_question_index(self):
        self.client.post("/start", data={"categories": "Biology"})
        response = self.client.post(
            "/answer",
            data={"question_index": "1", "answer": "A"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

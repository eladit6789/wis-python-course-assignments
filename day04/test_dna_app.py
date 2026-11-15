import unittest

import dna_app


class DnaCalculatorAppTests(unittest.TestCase):
    def setUp(self):
        dna_app.app.config.update(TESTING=True)
        self.client = dna_app.app.test_client()

    def test_calculator_shows_composition(self):
        response = self.client.post("/", data={"sequence": "AACCGT\n"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<title>DNA Composition Calculator</title>", response.data)
        self.assertIn(b"33.33%", response.data)
        self.assertIn(b"CG", response.data)
        self.assertIn(b"AT", response.data)
        self.assertIn(b"50.00%", response.data)

    def test_calculator_shows_validation_errors(self):
        for sequence, message in (
            ("", "The DNA sequence cannot be empty."),
            ("ACGTN", "Invalid DNA characters: N"),
        ):
            with self.subTest(sequence=sequence):
                response = self.client.post("/", data={"sequence": sequence})
                self.assertEqual(response.status_code, 200)
                self.assertIn(message.encode(), response.data)
                self.assertNotIn(b"Nucleotide percentages", response.data)


if __name__ == "__main__":
    unittest.main()

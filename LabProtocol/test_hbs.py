from io import BytesIO
from html.parser import HTMLParser
import unittest

from docx import Document
from werkzeug.datastructures import MultiDict

from app import app
from hbs_calculations import calculate_hbs_master_mix
from hbs_procedure import build_hbs_procedure


class HiddenFormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.current = []
            self.forms.append(self.current)
        elif tag == "input" and self.current is not None:
            if attrs.get("type") == "hidden" and "name" in attrs:
                self.current.append((attrs["name"], attrs.get("value", "")))

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None


def example_acids(reporter_concentration=30):
    return [
        {"name": "Firefly", "amount_per_well_ng": 50,
         "stock_concentration_ng_per_ul": 50},
        {"name": "Renilla", "amount_per_well_ng": 30,
         "stock_concentration_ng_per_ul": reporter_concentration},
        {"name": "GFP", "amount_per_well_ng": 10,
         "stock_concentration_ng_per_ul": 25},
    ]


class HbsCalculationTests(unittest.TestCase):
    def test_example_for_five_wells(self):
        mix = calculate_hbs_master_mix(example_acids(), 5, 0, 1000, 500)
        self.assertAlmostEqual(mix["water_per_well_ul"], 40.78)
        self.assertAlmostEqual(mix["water_total_ul"], 203.9)
        self.assertAlmostEqual(mix["nucleic_acids"][0]["total_volume_ul"], 9.1)
        self.assertEqual(mix["cacl2_total_ul"], 25)
        self.assertEqual(mix["hbs_total_ul"], 250)
        self.assertEqual(mix["total_mixture_volume_ul"], 500)

    def test_different_reporter_concentration_and_excess(self):
        mix = calculate_hbs_master_mix(example_acids(28.8), 4, 25, 1000, 500)
        self.assertAlmostEqual(mix["nucleic_acids"][2]["volume_per_well_ul"], 30 / 28.8)
        self.assertAlmostEqual(mix["water_total_ul"], (45 - 0.4 - 1 - 30 / 28.8 - 1.82) * 5)

    def test_rejects_missing_dna_excess_mass_and_overfilled_mix(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            calculate_hbs_master_mix([], 1, 0, 1000, 500)
        with self.assertRaisesRegex(ValueError, "exceeds the target"):
            calculate_hbs_master_mix(example_acids(), 1, 0, 50, 500)
        with self.assertRaisesRegex(ValueError, "exceed the 50"):
            calculate_hbs_master_mix(example_acids(0.1), 1, 0, 1000, 500)
        with self.assertRaisesRegex(ValueError, "pGEM stock"):
            calculate_hbs_master_mix(example_acids(), 1, 0, 1000, None)

    def test_procedure_uses_actual_order_and_no_unneeded_carrier(self):
        mix = calculate_hbs_master_mix(example_acids(28.8), 4, 25, 90, None)
        procedure = build_hbs_procedure({
            "treatment_configs": [{"treatment": "Reporter",
                                   "number_of_wells": 4, "master_mix": mix}],
            "incubation_time_hours": 24
        })
        additions = ["".join(segment["text"] for segment in substep)
                     for substep in procedure[2]["substeps"]]
        self.assertIn("1. Add DDW", additions[0])
        self.assertIn("2. Add Firefly: 5 µL total (1 µL", additions[1])
        self.assertIn("3. Add Renilla: 5.208333333 µL total (1.041666667 µL", additions[2])
        self.assertIn("4. Add GFP: 2 µL total (0.4 µL", additions[3])
        self.assertIn("5. Add 2.5 M CaCl2", additions[4])
        self.assertFalse(any("pGEM" in item for item in additions))


class HbsRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.form = {
            "strains": "WT", "treatments": "Renilla",
            "technical_replicates": "5", "culture_format": "24_well_plate",
            "group_replicates_0": "5",
            "preparation_excess_percent": "0", "target_total_acid_ng": "1000",
            "empty_vector_concentration": "500",
            "temperature_celsius": "37", "co2_percent": "5",
            "incubation_time_hours": "24",
            "protocol_name": "HBS example",
            "acid_name_0": ["Firefly", "Renilla", "GFP"],
            "acid_amount_0": ["50", "30", "10"],
            "acid_concentration_0": ["50", "30", "25"],
        }

    def test_setup_calculation_protocol_and_word_download(self):
        self.assertIn(b"/transfection/hbs", self.client.get("/new-protocol").data)
        setup = self.client.post("/transfection/hbs", data={
            "stage": "setup", "strains": "WT", "treatments": "Renilla",
            "technical_replicates": "5", "culture_format": "24_well_plate",
        })
        self.assertEqual(setup.status_code, 200)
        self.assertIn(b"Firefly (control)", setup.data)
        self.assertLess(setup.data.index(b"Firefly (control)"),
                        setup.data.index(b"Renilla (Renilla)"))
        self.assertLess(setup.data.index(b"Renilla (Renilla)"),
                        setup.data.index(b'value="GFP"'))
        self.assertIn(b'value="1000"', setup.data)
        self.assertIn(b'value="24.0"', setup.data)
        for stage in ("save_nucleic_acids", "generate_protocol"):
            response = self.client.post(
                "/transfection/hbs", data={**self.form, "stage": stage}
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"203.900", response.data)
            self.assertIn(b"250.000", response.data)
            self.assertIn(b"2.5 M CaCl2", response.data)
            self.assertNotIn(b"JetPRIME", response.data)
        self.assertIn(b'name="target_total_acid_ng" value="1000.0"', response.data)
        procedure_text = response.get_data(as_text=True)
        ordered_additions = [
            "1. Add DDW: 203.9 µL total (40.78 µL per well).",
            "2. Add Empty Vector (pGEM): 9.1 µL total (1.82 µL and 910 ng per well).",
            "3. Add Firefly: 5 µL total (1 µL and 50 ng per well).",
            "4. Add Renilla: 5 µL total (1 µL and 30 ng per well).",
            "5. Add GFP: 2 µL total (0.4 µL and 10 ng per well).",
            "6. Add 2.5 M CaCl2: 25 µL total (5 µL per well).",
            "8. Add 250 µL 2x HBS dropwise",
        ]
        positions = [procedure_text.index(text) for text in ordered_additions]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Wait 24 hours after transfection before harvesting.", procedure_text)

        parser = HiddenFormParser()
        parser.feed(response.get_data(as_text=True))
        download_form = next(
            MultiDict(form) for form in parser.forms
            if ("stage", "download_docx") in form
        )
        response = self.client.post("/transfection/hbs", data=download_form)
        self.assertEqual(response.status_code, 200)
        doc = Document(BytesIO(response.data))
        text = "\n".join(
            [p.text for p in doc.paragraphs]
            + [cell.text for table in doc.tables for row in table.rows for cell in row.cells]
        )
        for value in ("203.9", "250", "2.5 M", "CaCl2", "2x HBS", "Day 3", "Confirm before use"):
            self.assertIn(value, text)
        positions = [text.index(addition) for addition in ordered_additions]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Wait 24 hours after transfection before harvesting.", text)
        self.assertNotIn("JetPRIME", text)

    def test_invalid_format_and_missing_reporter_stock(self):
        bad_format = self.client.post("/transfection/hbs", data={
            **self.form, "stage": "setup", "culture_format": "6_well_plate"
        })
        self.assertIn(b"Select a valid culture format", bad_format.data)
        missing_stock = self.client.post("/transfection/hbs", data={
            **self.form, "stage": "generate_protocol",
            "acid_concentration_0": ["50", "", "25"]
        })
        self.assertIn(b"original stock", missing_stock.data)
        self.assertNotIn(b"Download Word document", missing_stock.data)


if __name__ == "__main__":
    unittest.main()

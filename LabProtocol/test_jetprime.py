from io import BytesIO
import unittest

from docx import Document
from docx.oxml.ns import qn
from docx.shared import RGBColor

from app import app
from jetprime_calculations import (
    calculate_group_master_mix,
    calculate_nucleic_acid_volume,
    calculate_number_of_plates,
    calculate_preparation_wells,
    calculate_total_wells
)
from jetprime_procedure import build_jetprime_procedure


class JetPrimeCalculationTests(unittest.TestCase):
    def test_treatment_master_mix_calculates_all_reagent_volumes(self):
        master_mix = calculate_group_master_mix(
            nucleic_acids=[{
                "name": "GFP plasmid",
                "amount_per_well_ng": 500,
                "stock_concentration_ng_per_ul": 1000
            }],
            number_of_wells=4
        )

        self.assertEqual(master_mix["preparation_wells"], 4.4)
        self.assertEqual(master_mix["total_nucleic_acid_ng_per_well"], 500)
        self.assertEqual(master_mix["buffer_volume_per_reaction_ul"], 0)
        self.assertEqual(master_mix["buffer_volume_ul"], 0)
        acid = master_mix["nucleic_acids"][0]
        self.assertEqual(acid["amount_per_well_ng"], 500)
        self.assertEqual(acid["stock_concentration_ng_per_ul"], 1000)
        self.assertAlmostEqual(acid["volume_per_well_ul"], 0.5)
        self.assertAlmostEqual(acid["total_volume_ul"], 2.2)
        self.assertAlmostEqual(
            master_mix["jetprime_volume_per_well_ul"], 1
        )
        self.assertAlmostEqual(master_mix["jetprime_volume_ul"], 4.4)
        self.assertAlmostEqual(master_mix["total_mixture_volume_ul"], 6.6)

    def test_unknown_buffer_keeps_mixture_volume_unconfirmed(self):
        master_mix = calculate_group_master_mix(
            nucleic_acids=[],
            number_of_wells=1,
            buffer_per_reaction_ul=None
        )

        self.assertIsNone(master_mix["buffer_volume_ul"])
        self.assertIsNone(master_mix["total_mixture_volume_ul"])

    def test_empty_vector_tops_up_user_nucleic_acids(self):
        master_mix = calculate_group_master_mix(
            nucleic_acids=[{
                "name": "GFP plasmid",
                "amount_per_well_ng": 300,
                "stock_concentration_ng_per_ul": 1000
            }],
            number_of_wells=2,
            excess_percent=0,
            target_total_acid_ng=500,
            empty_vector_concentration=1000
        )

        empty_vector = master_mix["nucleic_acids"][1]
        self.assertEqual(empty_vector["name"], "Empty Vector (pGEM)")
        self.assertEqual(empty_vector["amount_per_well_ng"], 200)
        self.assertEqual(empty_vector["stock_concentration_ng_per_ul"], 1000)
        self.assertEqual(master_mix["total_nucleic_acid_ng_per_well"], 500)

    def test_calculations_reject_invalid_values(self):
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            calculate_nucleic_acid_volume(100, 0)
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            calculate_nucleic_acid_volume(-1, 100)
        with self.assertRaisesRegex(ValueError, "JetPRIME ratio"):
            calculate_group_master_mix([], 1, jetprime_ratio=0)
        with self.assertRaisesRegex(ValueError, "Preparation excess"):
            calculate_preparation_wells(1, excess_percent=-1)

    def test_experiment_well_counts_include_replicates(self):
        self.assertEqual(calculate_total_wells(3, 2, 2), 12)
        self.assertEqual(calculate_number_of_plates(8, 6), 2)

    def test_lipofectamine_procedure_uses_two_dilution_tubes(self):
        master_mix = calculate_group_master_mix(
            nucleic_acids=[{
                "name": "GFP plasmid",
                "amount_per_well_ng": 500,
                "stock_concentration_ng_per_ul": 1000
            }],
            number_of_wells=4,
            excess_percent=10,
            buffer_per_reaction_ul=100
        )
        master_mix["lipofectamine_volume_ul"] = 4
        master_mix["lipofectamine_volume_per_well_ul"] = 1

        protocol = {
            "method_name": "Lipofectamine 2000",
            "protocol_name": "Lipofectamine Protocol",
            "culture_format": "6_well_plate",
            "culture_format_settings": {"label": "6-well plate"},
            "incubation_time_hours": None,
            "temperature_celsius": 37,
            "co2_percent": 5,
            "treatment_configs": [{
                "treatment": "GFP",
                "master_mix": master_mix
            }]
        }
        manufacturer_settings = {
            "reagent_name": "Lipofectamine 2000",
            "recommended_confluency": "70%",
            "manufacturer_protocol": {
                "cell_seeding": {},
                "dna_transfection": {
                    "serum_during_transfection": True,
                    "buffer_name": "Opti-MEM",
                    "dna_dilution_vortex_seconds": 10,
                    "complex_vortex_seconds": 1,
                    "complex_incubation_minutes": 20,
                    "complex_incubation_temperature": "room temperature",
                    "cell_incubation_minimum_hours": 24,
                    "cell_incubation_maximum_hours": 48
                }
            }
        }

        procedures = build_jetprime_procedure(
            protocol,
            manufacturer_settings
        )
        procedure_text = "\n".join(
            segment["text"]
            for step in procedures
            for substep in step["substeps"]
            for segment in substep
        )
        self.assertIn("Dilute DNA:", procedure_text)
        self.assertIn("220 µL", procedure_text)
        self.assertIn("Dilute Reagent:", procedure_text)
        self.assertIn("4 µL", procedure_text)
        self.assertNotIn(
            "Incubate the diluted reagent for 5 minutes.",
            procedure_text
        )
        self.assertIn(
            "Combine the diluted DNA and diluted reagent",
            procedure_text
        )
        self.assertIn("20 minutes at room temperature", procedure_text)
        self.assertNotIn("No complete nucleic-acid", procedure_text)


class JetPrimeRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_existing_home_and_protocol_pages_still_load(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/new-protocol").status_code, 200)

    def test_lipofectamine_is_available_from_method_pages(self):
        new_protocol = self.client.get("/new-protocol")
        lipofectamine = self.client.get("/transfection/lipofectamine")

        self.assertEqual(new_protocol.status_code, 200)
        self.assertIn(
            b"/transfection/lipofectamine",
            new_protocol.data
        )
        self.assertEqual(lipofectamine.status_code, 200)
        self.assertIn(
            b"Lipofectamine 2000 Experiment Setup",
            lipofectamine.data
        )

    def test_lipofectamine_displays_source_values_for_supported_formats(self):
        source_values = {
            "96_well_plate": (
                b"10,000\xe2\x80\x9340,000",
                b"100 ng per well",
                b"0.2\xe2\x80\x930.5",
                b"10 \xc2\xb5L"
            ),
            "24_well_plate": (
                b"50,000\xe2\x80\x93200,000",
                b"500 ng per well",
                b"1\xe2\x80\x932.5",
                b"50 \xc2\xb5L"
            ),
            "6_well_plate": (
                b"250,000\xe2\x80\x931,000,000",
                b"2500 ng per well",
                b"5\xe2\x80\x9312.5",
                b"250 \xc2\xb5L"
            )
        }
        for culture_format, values in source_values.items():
            with self.subTest(culture_format=culture_format):
                response = self.client.post(
                    "/transfection/lipofectamine",
                    data={
                        "stage": "setup",
                        "strains": ["WT"],
                        "treatments": ["GFP"],
                        "technical_replicates": "1",
                        "culture_format": culture_format
                    }
                )

                self.assertEqual(response.status_code, 200)
                html = b" ".join(response.data.split())
                for value in values:
                    self.assertIn(value, html)
                self.assertIn(
                    b"MAN0007824, Rev. 1.0 (2013)",
                    html
                )

    def test_lipofectamine_keeps_unlisted_formats_unconfirmed(self):
        response = self.client.post(
            "/transfection/lipofectamine",
            data={
                "stage": "setup",
                "strains": ["WT"],
                "treatments": ["GFP"],
                "technical_replicates": "1",
                "culture_format": "12_well_plate"
            }
        )

        self.assertEqual(response.status_code, 200)
        html = b" ".join(response.data.split())
        self.assertIn(
            b"does not specify setup amounts for 12-well plate",
            html
        )
        self.assertIn(b"Confirm cell seeding, DNA, reagent", html)

    def test_culture_format_selector_lists_all_requested_vessels(self):
        response = self.client.get("/jetprime")

        self.assertEqual(response.status_code, 200)
        for label in (
            b"96-well plate",
            b"24-well plate",
            b"12-well plate",
            b"6-well plate",
            b"60 mm dish",
            b"100 mm dish",
            b"150 mm dish"
        ):
            self.assertIn(label, response.data)

    def test_invalid_culture_format_is_reported(self):
        response = self.client.post("/jetprime", data={
            "stage": "setup",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "culture_format": "unsupported_format"
        })

        self.assertIn(b"Select a valid culture format.", response.data)

    def test_invalid_replicates_are_reported_and_preserved(self):
        response = self.client.post("/jetprime", data={
            "stage": "setup",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "0",
            "culture_format": "6_well_plate"
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Technical replicates must be a whole number", response.data)
        self.assertIn(b'value="0"', response.data)

    def test_setup_creates_each_strain_treatment_group_and_well(self):
        response = self.client.post("/jetprime", data={
            "stage": "setup",
            "strains": ["WT", "R116D"],
            "treatments": ["GFP", "Poly(I:C)"],
            "technical_replicates": "2",
            "culture_format": "6_well_plate"
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"5. Experimental Groups", response.data)

    def test_setup_shows_a_well_count_for_every_experimental_group(self):
        response = self.client.post("/jetprime", data={
            "stage": "setup",
            "strains": ["WT", "R116D"],
            "treatments": ["GFP", "Control"],
            "technical_replicates": "2",
            "culture_format": "6_well_plate"
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'name="group_replicates_'), 4)
        self.assertIn(b'aria-label="Wells for WT - GFP"', response.data)
        self.assertIn(b'aria-label="Wells for R116D - Control"', response.data)

    def test_invalid_group_well_count_is_reported_and_preserved(self):
        response = self.client.post("/jetprime", data={
            "stage": "save_nucleic_acids",
            "strains": ["WT", "R116D"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "culture_format": "6_well_plate",
            "group_replicates_0": "2",
            "group_replicates_1": "0"
        })

        self.assertEqual(response.status_code, 200)
        html = b" ".join(response.data.split())
        self.assertIn(b"Group 2: number of wells must be a whole number", html)
        self.assertIn(b'name="group_replicates_1"', html)
        self.assertIn(b'value="0"', html)

    def test_invalid_nucleic_acid_is_reported_and_preserved(self):
        response = self.client.post("/jetprime", data={
            "stage": "save_nucleic_acids",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "culture_format": "6_well_plate",
            "acid_name_0": ["GFP plasmid"],
            "acid_amount_0": ["not-a-number"],
            "acid_concentration_0": ["500"]
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"nucleic-acid amount and stock concentration must be numbers", response.data)
        self.assertIn(b'value="not-a-number"', response.data)

    def test_missing_stock_concentration_blocks_protocol_export(self):
        response = self.client.post("/jetprime", data={
            "stage": "download_docx",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "group_replicates_0": "1",
            "culture_format": "6_well_plate",
            "acid_name_0": ["GFP plasmid"],
            "acid_amount_0": ["500"],
            "acid_concentration_0": [""]
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/html")
        self.assertIn(
            b"enter the original stock concentration for GFP plasmid in ng/",
            response.data
        )

    def test_multi_plate_layout_preserves_group_replicate_numbers(self):
        response = self.client.post("/jetprime", data={
            "stage": "download_docx",
            "strains": ["WT", "KO"],
            "treatments": ["Control"],
            "technical_replicates": "1",
            "group_replicates_0": "5",
            "group_replicates_1": "3",
            "culture_format": "6_well_plate",
            "include_checklist": "false"
        })

        self.assertEqual(response.status_code, 200)
        document = Document(BytesIO(response.data))
        plate_labels = [
            paragraph.text for paragraph in document.paragraphs
            if paragraph.style.name == "Heading 2"
            and paragraph.text.startswith("Plate ")
        ]
        self.assertEqual(plate_labels, ["Plate 1", "Plate 2"])
        overview = {
            row.cells[0].text: row.cells[1].text
            for row in document.tables[0].rows
        }
        self.assertEqual(overview["Experimental wells"], "8")
        self.assertEqual(overview["Plates or dishes required"], "2 plates")
        plate_tables = document.tables[1:3]
        self.assertEqual(len(plate_tables), 2)
        self.assertEqual(
            plate_tables[0].cell(1, 2).text,
            "B3\nKO\nControl\nRep 1"
        )
        self.assertEqual(
            plate_tables[1].cell(0, 0).text,
            "A1\nKO\nControl\nRep 2"
        )
        self.assertEqual(
            plate_tables[1].cell(0, 1).text,
            "A2\nKO\nControl\nRep 3"
        )

    def test_ninety_six_well_layout_is_split_into_readable_panels(self):
        response = self.client.post("/jetprime", data={
            "stage": "download_docx",
            "strains": ["WT"],
            "treatments": ["Control"],
            "technical_replicates": "1",
            "group_replicates_0": "96",
            "culture_format": "96_well_plate",
            "include_checklist": "false"
        })

        self.assertEqual(response.status_code, 200)
        document = Document(BytesIO(response.data))
        self.assertIn("Columns 1–6", [p.text for p in document.paragraphs])
        self.assertIn("Columns 7–12", [p.text for p in document.paragraphs])
        left_panel, right_panel = document.tables[1:3]
        self.assertEqual(
            (len(left_panel.rows), len(left_panel.columns)),
            (8, 6)
        )
        for layout_table in (left_panel, right_panel):
            borders = layout_table._tbl.tblPr.find(qn("w:tblBorders"))
            self.assertTrue(all(
                edge.get(qn("w:color")) == "000000"
                for edge in borders
            ))
        self.assertEqual(
            right_panel.cell(7, 5).text,
            "H12\nWT\nControl\nRep 96"
        )

    def test_twelve_and_twenty_four_well_layout_dimensions(self):
        for culture_format, expected_rows, expected_columns in (
            ("12_well_plate", 3, 4),
            ("24_well_plate", 4, 6)
        ):
            with self.subTest(culture_format=culture_format):
                response = self.client.post("/jetprime", data={
                    "stage": "download_docx",
                    "strains": ["WT"],
                    "treatments": ["Control"],
                    "technical_replicates": "1",
                    "group_replicates_0": "1",
                    "culture_format": culture_format,
                    "include_checklist": "false"
                })

                self.assertEqual(response.status_code, 200)
                document = Document(BytesIO(response.data))
                layout = document.tables[1]
                self.assertEqual(
                    (len(layout.rows), len(layout.columns)),
                    (expected_rows, expected_columns)
                )

    def test_valid_submission_shows_per_treatment_master_mix(self):
        response = self.client.post("/jetprime", data={
            "stage": "save_nucleic_acids",
            "strains": ["WT", "R116D"],
            "treatments": ["GFP"],
            "technical_replicates": "2",
            "culture_format": "6_well_plate",
            "jetprime_ratio": "2",
            "preparation_excess_percent": "10",
            "acid_name_0": ["GFP plasmid"],
            "acid_amount_0": ["500"],
            "acid_concentration_0": ["1000"]
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Reaction-equivalents to prepare:</strong>\n            4.4", response.data)
        self.assertIn(b"GFP plasmid", response.data)
        html = b" ".join(response.data.split())
        self.assertIn(
            b"Post-transfection incubation:</strong> 24\xe2\x80\x9348 hours",
            html
        )
        self.assertIn(b"Temperature:</strong> 37.00", html)
        self.assertIn("CO₂ concentration:</strong> 5.00".encode(), html)
        self.assertIn(b"Manufacturer buffer per reaction:</strong> 200.000", html)
        self.assertIn(
            b"Total transfection mixture to prepare:</strong> 886.600",
            html
        )

    def test_incubation_settings_are_displayed(self):
        response = self.client.post("/jetprime", data={
            "stage": "save_nucleic_acids",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "culture_format": "6_well_plate",
            "incubation_time_hours": "24",
            "temperature_celsius": "36.5",
            "co2_percent": "5.5",
            "acid_name_0": [""],
            "acid_amount_0": [""],
            "acid_concentration_0": [""]
        })

        self.assertEqual(response.status_code, 200)
        html = b" ".join(response.data.split())
        self.assertIn(
            b"Post-transfection incubation:</strong> 24.00 hours",
            html
        )
        self.assertIn(b"Temperature:</strong> 36.50", html)
        self.assertIn("CO₂ concentration:</strong> 5.50".encode(), html)

    def test_lipofectamine_protocol_uses_source_format_values(self):
        response = self.client.post("/transfection/lipofectamine", data={
            "stage": "generate_protocol",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "culture_format": "6_well_plate",
            "reagent_ratio": "3",
            "preparation_excess_percent": "10",
            "incubation_time_hours": "24",
            "acid_name_0": ["GFP plasmid"],
            "acid_amount_0": ["2500"],
            "acid_concentration_0": ["1000"]
        })

        self.assertEqual(response.status_code, 200)
        html = b" ".join(response.data.split())
        self.assertIn(b"250,000\xe2\x80\x931,000,000 cells", html)
        self.assertIn(b"6, 9, 12, 15", html)
        self.assertIn(b"165 \xc2\xb5L", html)
        self.assertIn(b"5 minutes at room temperature", html)
        self.assertIn(
            b"<strong>250 \xc2\xb5L</strong> of prepared mixture",
            html
        )
        self.assertIn(b"manufacturer duration is 24\xe2\x80\x9372 hours", html)
        self.assertIn(b'name="reagent_ratio"', html)

    def test_invalid_incubation_temperature_is_reported_and_preserved(self):
        response = self.client.post("/jetprime", data={
            "stage": "save_nucleic_acids",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "culture_format": "6_well_plate",
            "temperature_celsius": "-5",
            "co2_percent": "5",
            "acid_name_0": [""],
            "acid_amount_0": [""],
            "acid_concentration_0": [""]
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Temperature must be greater than zero.", response.data)
        self.assertIn(b'value="-5"', response.data)

    def test_each_treatment_uses_its_own_nucleic_acid_mix(self):
        response = self.client.post("/jetprime", data={
            "stage": "save_nucleic_acids",
            "strains": ["WT", "R116D"],
            "treatments": ["GFP", "Poly(I:C)"],
            "technical_replicates": "1",
            "culture_format": "24_well_plate",
            "jetprime_ratio": "2",
            "preparation_excess_percent": "0",
            "acid_name_0": ["GFP plasmid"],
            "acid_amount_0": ["500"],
            "acid_concentration_0": ["1000"],
            "acid_name_1": ["Poly(I:C)"],
            "acid_amount_1": ["750"],
            "acid_concentration_1": ["1500"]
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"GFP plasmid", response.data)
        self.assertIn(b"Poly(I:C)", response.data)
        self.assertIn(b"500.000", response.data)
        self.assertIn(b"750.000", response.data)
        self.assertIn(b"Strains receiving treatment:</strong>\n            WT, R116D", response.data)

    def test_group_well_counts_drive_totals_and_treatment_mix_sizes(self):
        response = self.client.post("/jetprime", data={
            "stage": "save_nucleic_acids",
            "strains": ["WT", "R116D"],
            "treatments": ["GFP", "Control"],
            "technical_replicates": "1",
            "culture_format": "6_well_plate",
            "preparation_excess_percent": "0",
            "group_replicates_0": "1",
            "group_replicates_1": "2",
            "group_replicates_2": "3",
            "group_replicates_3": "4",
            "acid_name_0": [""],
            "acid_amount_0": [""],
            "acid_concentration_0": [""],
            "acid_name_1": [""],
            "acid_amount_1": [""],
            "acid_concentration_1": [""]
        })

        self.assertEqual(response.status_code, 200)
        html = b" ".join(response.data.split())
        self.assertIn(b"<strong>Number of wells:</strong> 4", html)
        self.assertIn(b"Reaction-equivalents to prepare:</strong> 4", html)
        self.assertIn(b"<strong>Number of wells:</strong> 6", html)
        self.assertIn(b"Reaction-equivalents to prepare:</strong> 6", html)

    def test_unverified_dish_values_are_not_guessed(self):
        response = self.client.post("/jetprime", data={
            "stage": "save_nucleic_acids",
            "strains": ["WT"],
            "treatments": ["Untreated"],
            "technical_replicates": "1",
            "culture_format": "60_mm_dish",
            "jetprime_ratio": "2",
            "preparation_excess_percent": "10",
            "acid_name_0": [""],
            "acid_amount_0": [""],
            "acid_concentration_0": [""]
        })

        self.assertEqual(response.status_code, 200)
        html = b" ".join(response.data.split())
        self.assertIn(
            b"Manufacturer buffer per reaction:</strong> Requires confirmation",
            html
        )
        self.assertIn(
            b"Total transfection mixture to prepare:</strong> Requires confirmation",
            html
        )

    def test_100_mm_dish_uses_verified_buffer_volume(self):
        response = self.client.post("/jetprime", data={
            "stage": "save_nucleic_acids",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "culture_format": "100_mm_dish",
            "jetprime_ratio": "2",
            "preparation_excess_percent": "0",
            "acid_name_0": [""],
            "acid_amount_0": [""],
            "acid_concentration_0": [""]
        })

        self.assertEqual(response.status_code, 200)
        html = b" ".join(response.data.split())
        self.assertIn(
            b"Manufacturer buffer per reaction:</strong> 500.000",
            html
        )

    def test_protocol_generation_includes_overview_mixes_and_warnings(self):
        response = self.client.post("/jetprime", data={
            "stage": "generate_protocol",
            "strains": ["WT", "R116D"],
            "treatments": ["GFP"],
            "technical_replicates": "2",
            "culture_format": "6_well_plate",
            "jetprime_ratio": "2",
            "preparation_excess_percent": "10",
            "incubation_time_hours": "24",
            "temperature_celsius": "37",
            "co2_percent": "5",
            "protocol_name": "GFP Transfection",
            "experimental_date": "2026-11-17",
            "include_checklist": "true",
            "acid_name_0": ["GFP plasmid"],
            "acid_amount_0": ["500"],
            "acid_concentration_0": ["1000"]
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<h1>GFP Transfection</h1>", response.data)
        self.assertIn(b"2026-11-17", response.data)
        self.assertIn(b"R116D", response.data)
        self.assertIn(b"GFP plasmid", response.data)
        self.assertIn(b"<td>1 plate</td>", response.data)
        self.assertIn(
            b'name="culture_format" value="6_well_plate"',
            response.data
        )
        self.assertIn(b"Experimental Procedure", response.data)
        self.assertIn(b"vortex for 10 seconds", response.data)
        self.assertIn(b"10 minutes at", response.data)
        self.assertIn(b"serum-containing medium", response.data)

    def test_protocol_generation_preserves_individual_group_well_counts(self):
        response = self.client.post("/jetprime", data={
            "stage": "generate_protocol",
            "strains": ["WT", "R116D"],
            "treatments": ["GFP", "Control"],
            "technical_replicates": "1",
            "culture_format": "6_well_plate",
            "preparation_excess_percent": "0",
            "group_replicates_0": "1",
            "group_replicates_1": "2",
            "group_replicates_2": "3",
            "group_replicates_3": "4",
            "acid_name_0": [""],
            "acid_amount_0": [""],
            "acid_concentration_0": [""],
            "acid_name_1": [""],
            "acid_amount_1": [""],
            "acid_concentration_1": [""]
        })

        self.assertEqual(response.status_code, 200)
        html = b" ".join(response.data.split())
        self.assertIn(b"<td>10</td>", html)
        self.assertIn(b"<td>1</td>", html)
        self.assertIn(b"<td>2</td>", html)
        self.assertIn(b"<td>3</td>", html)
        self.assertIn(b"<td>4</td>", html)
        self.assertIn(b"<p><strong>Experimental vessels:</strong> 4</p>", html)
        self.assertIn(b"<p><strong>Experimental vessels:</strong> 6</p>", html)
        self.assertIn(b'name="group_replicates_0" value="1"', html)
        self.assertIn(b'name="group_replicates_3" value="4"', html)

    def test_protocol_checklist_can_be_disabled(self):
        response = self.client.post("/jetprime", data={
            "stage": "generate_protocol",
            "strains": ["WT"],
            "treatments": ["Untreated"],
            "technical_replicates": "1",
            "culture_format": "24_well_plate",
            "jetprime_ratio": "2",
            "preparation_excess_percent": "10",
            "temperature_celsius": "37",
            "co2_percent": "5",
            "protocol_name": "No checklist",
            "experimental_date": "",
            "include_checklist": "false",
            "acid_name_0": [""],
            "acid_amount_0": [""],
            "acid_concentration_0": [""]
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<h1>No checklist</h1>", response.data)
        self.assertNotIn(b"Practical Checklist", response.data)

    def test_invalid_experimental_date_prevents_protocol_generation(self):
        response = self.client.post("/jetprime", data={
            "stage": "generate_protocol",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "culture_format": "6_well_plate",
            "protocol_name": "Invalid date",
            "experimental_date": "not-a-date",
            "temperature_celsius": "37",
            "co2_percent": "5",
            "acid_name_0": [""],
            "acid_amount_0": [""],
            "acid_concentration_0": [""]
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Enter the experimental date using the date picker.",
            response.data
        )
        self.assertNotIn(b"<h1>Invalid date</h1>", response.data)

    def test_word_export_contains_calculations_and_confirmation_warnings(self):
        response = self.client.post("/jetprime", data={
            "stage": "download_docx",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "culture_format": "60_mm_dish",
            "jetprime_ratio": "2",
            "preparation_excess_percent": "10",
            "group_replicates_0": "3",
            "temperature_celsius": "37",
            "co2_percent": "5",
            "protocol_name": "No checklist export",
            "experimental_date": "",
            "include_checklist": "false",
            "acid_name_0": [""],
            "acid_amount_0": [""],
            "acid_concentration_0": [""]
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.mimetype,
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )
        self.assertIn("No_checklist_export.docx", response.headers["Content-Disposition"])
        self.assertTrue(response.data.startswith(b"PK"))

        document = Document(BytesIO(response.data))
        document_text = "\n".join(
            [paragraph.text for paragraph in document.paragraphs]
            + [
                cell.text
                for table in document.tables
                for row in table.rows
                for cell in row.cells
            ]
        )
        self.assertIn("No checklist export", document_text)
        self.assertIn("Prepare 3.3 reaction-equivalents", document_text)
        self.assertIn("3 dishes", document_text)
        self.assertIn("Requires confirmation", document_text)
        self.assertIn(
            "does not specify cells per vessel or growth-medium volume",
            document_text
        )
        self.assertIn(
            "Do not use this mix until confirmed",
            document_text
        )
        self.assertNotIn("Practical Checklist", document_text)
        self.assertNotIn("Experimental Groups", document_text)
        self.assertNotIn("Final Notes and Confirmations", document_text)

    def test_word_export_is_compact_and_shows_bench_ready_reagent_volumes(self):
        response = self.client.post("/jetprime", data={
            "stage": "download_docx",
            "strains": ["WT"],
            "treatments": ["GFP"],
            "technical_replicates": "1",
            "group_replicates_0": "2",
            "culture_format": "6_well_plate",
            "jetprime_ratio": "2",
            "preparation_excess_percent": "10",
            "temperature_celsius": "37",
            "co2_percent": "5",
            "protocol_name": "Compact Protocol",
            "include_checklist": "false",
            "acid_name_0": ["GFP plasmid"],
            "acid_amount_0": ["500"],
            "acid_concentration_0": ["1000"]
        })

        self.assertEqual(response.status_code, 200)
        document = Document(BytesIO(response.data))
        heading_one_text = [
            paragraph.text for paragraph in document.paragraphs
            if paragraph.style.name == "Heading 1"
        ]
        self.assertEqual(
            heading_one_text,
            [
                "1. Experimental Overview",
                "2. Plate Layout",
                "3. Reagent Preparation",
                "4. Procedure"
            ]
        )
        document_text = "\n".join(
            [paragraph.text for paragraph in document.paragraphs]
            + [
                cell.text
                for table in document.tables
                for row in table.rows
                for cell in row.cells
            ]
        )
        self.assertIn("Prepare 2.2 reaction-equivalents", document_text)
        self.assertIn("totals include 10% preparation excess", document_text)
        self.assertIn("Cell strains", document_text)
        self.assertIn("Technical replicates per group", document_text)
        self.assertIn("Experimental wells", document_text)
        self.assertIn("Plates or dishes required", document_text)
        self.assertIn("A1", document_text)
        self.assertIn("Rep 1", document_text)
        self.assertIn(
            "Prepare a separate mixture for each treatment.",
            document_text
        )
        self.assertNotIn("Label one tube for each treatment", document_text)
        self.assertIn("vortex for 10 seconds", document_text)
        self.assertIn("Vortex each mixture for 1 second", document_text)
        self.assertIn("10 minutes at room temperature", document_text)
        self.assertIn("serum-containing medium", document_text)
        self.assertIn(
            "GFP: add 201.5 µL of prepared mixture to each assigned well "
            "across all strains receiving this treatment.",
            document_text
        )
        self.assertIn(
            "GFP: add the total nucleic acid volume(s) GFP plasmid 1.1 µL "
            "to 440 µL jetPRIME buffer.",
            document_text
        )
        self.assertIn(
            "GFP: add 2.2 µL JetPRIME to its nucleic-acid dilution.",
            document_text
        )
        procedure_paragraphs = [
            paragraph for paragraph in document.paragraphs
            if paragraph.text.startswith(
                ("GFP: add the total nucleic acid volume(s)",
                 "GFP: add ",
                 "GFP: add 201")
            )
        ]
        for paragraph in procedure_paragraphs:
            for run in paragraph.runs:
                if "µL" in run.text:
                    self.assertTrue(run.bold)
        self.assertIn(
            "use the manufacturer's complete protocol for siRNA-only",
            document_text
        )
        self.assertIn("Incubate for 24–48 hours", document_text)
        self.assertIn("Use the selected settings of 37 °C and 5% CO₂", document_text)
        self.assertIn("Source: Sartorius jetPRIME Short Protocol - DNA Transfection", document_text)
        self.assertNotIn("verify the current manufacturer", document_text)
        self.assertNotIn("Confirm the manufacturer's", document_text)
        self.assertNotIn("Experimental Groups", document_text)
        self.assertNotIn("Incubation Settings", document_text)
        self.assertNotIn("Practical Checklist", document_text)

        overview_rows = {
            row.cells[0].text: row.cells[1].text
            for row in document.tables[0].rows
        }
        self.assertEqual(overview_rows["Experimental wells"], "2")
        self.assertEqual(
            overview_rows["Technical replicates per group"],
            "WT / GFP: 2"
        )
        layout_table = document.tables[1]
        self.assertEqual(len(layout_table.rows), 2)
        self.assertEqual(len(layout_table.columns), 3)
        self.assertEqual(layout_table.cell(0, 0).text, "A1\nWT\nGFP\nRep 1")
        self.assertEqual(layout_table.cell(0, 1).text, "A2\nWT\nGFP\nRep 2")
        self.assertEqual(layout_table.cell(1, 2).text, "B3\nEmpty")

        reagent_table = document.tables[2]
        self.assertEqual(
            [cell.text for cell in reagent_table.rows[0].cells],
            [
                "Component",
                "Stock concentration\n(ng/µL)",
                "Amount per well\n(ng)",
                "Volume per well\n(µL)",
                "Total volume to prepare\n(µL)"
            ]
        )
        table_rows = {
            row.cells[0].text: [cell.text for cell in row.cells]
            for row in reagent_table.rows[1:]
        }
        self.assertEqual(
            table_rows["GFP plasmid"],
            ["GFP plasmid", "1000", "500", "0.5 µL", "1.1 µL"]
        )
        self.assertEqual(
            table_rows["JetPRIME"],
            ["JetPRIME", "N/A", "N/A", "1 µL", "2.2 µL"]
        )
        self.assertEqual(
            table_rows["Buffer"],
            ["Buffer", "N/A", "N/A", "200 µL", "440 µL"]
        )
        reagent_row = reagent_table.rows[1]
        for column_index in (0, 4):
            self.assertTrue(
                reagent_row.cells[column_index].paragraphs[0].runs[0].bold
            )
        for column_index in (1, 2, 3):
            self.assertFalse(
                reagent_row.cells[column_index].paragraphs[0].runs[0].bold
            )
        self.assertEqual(
            document.styles["Heading 1"].font.color.rgb,
            RGBColor(0, 0, 0)
        )
        for cell in reagent_table.rows[0].cells:
            self.assertIsNone(cell._tc.tcPr.find(qn("w:shd")))


if __name__ == "__main__":
    unittest.main()

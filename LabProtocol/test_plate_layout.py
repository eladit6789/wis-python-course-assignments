import unittest

from plate_layout import build_plate_layout


class PlateLayoutTests(unittest.TestCase):
    def test_assigns_groups_row_major_and_leaves_unused_wells_empty(self):
        layouts = build_plate_layout(
            [
                {
                    "strain": "WT",
                    "treatment": "Control",
                    "technical_replicates": 2
                },
                {
                    "strain": "KO",
                    "treatment": "Drug",
                    "technical_replicates": 1
                }
            ],
            rows=2,
            columns=3
        )

        self.assertEqual(len(layouts), 1)
        wells = layouts[0]["rows"]
        self.assertEqual(
            (wells[0][0]["position"], wells[0][0]["strain"],
             wells[0][0]["treatment"], wells[0][0]["replicate"]),
            ("A1", "WT", "Control", 1)
        )
        self.assertEqual(wells[0][1]["replicate"], 2)
        self.assertEqual(
            (wells[0][2]["position"], wells[0][2]["strain"],
             wells[0][2]["treatment"], wells[0][2]["replicate"]),
            ("A3", "KO", "Drug", 1)
        )
        self.assertEqual(wells[1][2], {
            "position": "B3",
            "strain": None,
            "treatment": None,
            "replicate": None
        })

    def test_keeps_replicate_numbers_when_a_group_crosses_plates(self):
        layouts = build_plate_layout(
            [{
                "strain": "WT",
                "treatment": "Control",
                "technical_replicates": 5
            }, {
                "strain": "KO",
                "treatment": "Drug",
                "technical_replicates": 3
            }],
            rows=2,
            columns=3
        )

        self.assertEqual([layout["label"] for layout in layouts], [
            "Plate 1",
            "Plate 2"
        ])
        self.assertEqual(layouts[0]["rows"][1][2]["replicate"], 1)
        self.assertEqual(layouts[1]["rows"][0][0]["replicate"], 2)
        self.assertEqual(layouts[1]["rows"][0][0]["strain"], "KO")
        self.assertEqual(layouts[1]["rows"][0][0]["treatment"], "Drug")
        self.assertEqual(layouts[1]["rows"][0][1]["replicate"], 3)

    def test_supports_ninety_six_well_coordinates(self):
        layouts = build_plate_layout(
            [{
                "strain": "WT",
                "treatment": "Control",
                "technical_replicates": 96
            }],
            rows=8,
            columns=12
        )

        self.assertEqual(len(layouts), 1)
        self.assertEqual(layouts[0]["rows"][0][0]["position"], "A1")
        self.assertEqual(layouts[0]["rows"][7][11]["position"], "H12")
        self.assertEqual(layouts[0]["rows"][7][11]["replicate"], 96)

    def test_supports_dish_labels(self):
        layouts = build_plate_layout(
            [{
                "strain": "WT",
                "treatment": "Control",
                "technical_replicates": 2
            }],
            rows=1,
            columns=1,
            container_label="Dish",
            position_prefix="Dish"
        )

        self.assertEqual([layout["label"] for layout in layouts], [
            "Dish 1",
            "Dish 2"
        ])
        self.assertEqual(layouts[1]["rows"][0][0]["position"], "Dish 2")
        self.assertEqual(layouts[1]["rows"][0][0]["replicate"], 2)


if __name__ == "__main__":
    unittest.main()

def _step(action, text, substeps=None):
    return {
        "action": action,
        "details": [{"text": text, "bold": False}],
        "substeps": [[{"text": text, "bold": False}] for text in (substeps or [])],
    }


def _volume(value):
    return f"{value:.10g}"


def build_hbs_procedure(protocol):
    steps = [
        _step(
            "Day 1: seed cells",
            "Seed 45,000 cells in 1 mL per 24-well; aim for 40% "
            "confluency on the day of transfection. The supplied example "
            "says to put cells on the walls; confirm what this means locally."
        ),
        _step(
            "Day 2: prepare reagents",
            "Remove 2x HBS and 2.5 M CaCl2 from the fridge."
        ),
    ]
    for config in protocol["treatment_configs"]:
        mix = config["master_mix"]
        additions = [
            f'Add DDW: {_volume(mix["water_total_ul"])} µL total '
            f'({_volume(mix["water_per_well_ul"])} µL per well).'
        ]
        for acid in mix["nucleic_acids"]:
            additions.append(
                f'Add {acid["name"]}: {_volume(acid["total_volume_ul"])} µL '
                f'total ({_volume(acid["volume_per_well_ul"])} µL and '
                f'{_volume(acid["amount_per_well_ng"])} ng per well).'
            )
        additions.append(
            f'Add 2.5 M CaCl2: {_volume(mix["cacl2_total_ul"])} µL total '
            f'({_volume(mix["cacl2_per_well_ul"])} µL per well).'
        )
        additions.append(
            f'The DNA/CaCl2 mixture is {_volume(50 * mix["preparation_wells"])} '
            "µL total. Vortex 2x HBS well at speed 8. Set the vortex to speed "
            "2 and check that it is not too strong."
        )
        additions.append(
            f'Add {_volume(mix["hbs_total_ul"])} µL 2x HBS dropwise '
            f'({_volume(mix["hbs_per_well_ul"])} µL per well) to the '
            "DNA/CaCl2 mixture while vortexing. Briefly vortex afterwards; "
            "do not spin down. The example describes preparing 2–3 samples together."
        )
        steps.append(_step(
            f'Prepare {config["treatment"]}',
            f'For {config["number_of_wells"]} wells, prepare '
            f'{mix["preparation_wells"]:g} reaction-equivalents '
            "in this order. Total volumes include the selected preparation excess.",
            [f"{index}. {addition}" for index, addition in enumerate(additions, 1)]
        ))
    steps.extend([
        _step(
            "Add mixture to cells",
            "Add 100 µL evenly to each assigned well; a color change may occur. "
            "Move the plate to the bench afterwards because the hood vibrates. "
            "The example describes approximately 2 minutes total before "
            "addition, without a timer; confirm the timing locally."
        ),
        _step(
            "Post-transfection incubation",
            (
                f'Wait {_volume(protocol["incubation_time_hours"])} hours '
                "after transfection before harvesting."
                if protocol["incubation_time_hours"] is not None
                else "The post-transfection duration is not specified; "
                "confirm it before harvesting."
            )
        ),
        _step(
            "Day 3: harvest",
            "Aspirate medium, add 0.5 mL cold PBS per well, aspirate PBS, "
            "add 100 µL 1x RLB per well, and shake for 5 minutes."
        ),
        _step(
            "Measure luminescence",
            "Use a luminescence-compatible 96-well plate. Transfer three "
            "5 µL aliquots from each well. The example specifies 25 µL "
            "Firefly mix and 50 µL Renilla mix per reaction, with CTZ "
            "1:1000 in phosphate buffer. The additional '1300mL' amounts "
            "are ambiguous; confirm them and the assay procedure before use. "
            "The example says to take Firefly mix from -50; confirm the "
            "temperature unit and storage conditions. "
            "Measure in a luminometer and analyze the results."
        ),
    ])
    return steps

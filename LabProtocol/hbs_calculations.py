from jetprime_calculations import (
    calculate_nucleic_acid_volume,
    calculate_preparation_wells,
    calculate_total_nucleic_acid,
)


def calculate_hbs_master_mix(
    nucleic_acids, number_of_wells, excess_percent, target_total_acid_ng,
    empty_vector_concentration
):
    """Calculate the 24-well DNA/CaCl2 mixture and equal-volume 2x HBS."""
    preparation_wells = calculate_preparation_wells(number_of_wells, excess_percent)
    if not nucleic_acids:
        raise ValueError("Enter at least one nucleic acid for each treatment.")
    total = calculate_total_nucleic_acid(nucleic_acids)
    if target_total_acid_ng is None or target_total_acid_ng <= 0:
        raise ValueError("Enter a positive target total DNA amount for HBS.")
    if total > target_total_acid_ng + 1e-9:
        raise ValueError("DNA amount exceeds the target total per well.")

    acids = list(nucleic_acids)
    carrier = target_total_acid_ng - total
    if carrier > 1e-9:
        if empty_vector_concentration is None:
            raise ValueError("Enter the pGEM stock concentration for the carrier.")
        acids.insert(0, {
            "name": "Empty Vector (pGEM)",
            "amount_per_well_ng": carrier,
            "stock_concentration_ng_per_ul": empty_vector_concentration,
        })

    results = []
    for acid in acids:
        volume = calculate_nucleic_acid_volume(
            acid["amount_per_well_ng"], acid["stock_concentration_ng_per_ul"]
        )
        results.append({
            **acid,
            "volume_per_well_ul": volume,
            "total_volume_ul": volume * preparation_wells,
        })

    water = 50 - 5 - sum(acid["volume_per_well_ul"] for acid in results)
    if water < -1e-9:
        raise ValueError("DNA and CaCl2 volumes exceed the 50 µL pre-HBS mixture.")
    water = max(0, water)
    return {
        "preparation_wells": preparation_wells,
        "nucleic_acids": results,
        "total_nucleic_acid_ng_per_well": total + max(0, carrier),
        "water_per_well_ul": water,
        "water_total_ul": water * preparation_wells,
        "cacl2_per_well_ul": 5,
        "cacl2_total_ul": 5 * preparation_wells,
        "hbs_per_well_ul": 50,
        "hbs_total_ul": 50 * preparation_wells,
        "transfection_mixture_volume_per_reaction_ul": 100,
        "total_mixture_volume_ul": 100 * preparation_wells,
    }

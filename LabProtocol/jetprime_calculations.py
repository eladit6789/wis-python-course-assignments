import math


def _finite_number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")
    if not math.isfinite(number):
        raise ValueError(f"{label} must be a finite number.")
    return number


def _positive_integer(value, label):
    number = _finite_number(value, label)
    if number < 1 or not number.is_integer():
        raise ValueError(f"{label} must be a whole number of at least 1.")
    return int(number)


def calculate_nucleic_acid_volume(amount_ng, concentration_ng_ul):
    """Calculate the volume of nucleic acid needed per well."""

    amount = _finite_number(amount_ng, "Nucleic-acid amount")
    concentration = _finite_number(
        concentration_ng_ul, "Stock concentration"
    )
    if amount < 0:
        raise ValueError("Nucleic-acid amount cannot be negative.")
    if concentration <= 0:
        raise ValueError("Stock concentration must be greater than zero.")

    return amount / concentration


def calculate_total_nucleic_acid(nucleic_acids):
    """Calculate the total nucleic acid amount per well."""

    amounts = [
        _finite_number(
            nucleic_acid["amount_per_well_ng"],
            "Nucleic-acid amount"
        )
        for nucleic_acid in nucleic_acids
    ]
    if any(amount < 0 for amount in amounts):
        raise ValueError("Nucleic-acid amount cannot be negative.")
    return sum(amounts)


def calculate_jetprime_volume(total_amount_ng, jetprime_ratio=2):
    """Calculate JetPRIME volume per well."""

    amount = _finite_number(total_amount_ng, "Total nucleic-acid amount")
    ratio = _finite_number(jetprime_ratio, "JetPRIME ratio")
    if amount < 0:
        raise ValueError("Total nucleic-acid amount cannot be negative.")
    if ratio <= 0:
        raise ValueError("JetPRIME ratio must be greater than zero.")

    return amount / 1000 * ratio


def calculate_preparation_wells(number_of_wells, excess_percent=10):
    """Calculate the number of reaction-equivalents to prepare."""

    wells = _positive_integer(number_of_wells, "Number of wells")
    excess = _finite_number(excess_percent, "Preparation excess")
    if excess < 0:
        raise ValueError("Preparation excess cannot be negative.")

    return wells * (1 + excess / 100)


def calculate_total_wells(
    number_of_strains,
    number_of_treatments,
    technical_replicates=1
):
    """Calculate the total number of experimental wells."""

    strains = _positive_integer(number_of_strains, "Number of strains")
    treatments = _positive_integer(
        number_of_treatments, "Number of treatments"
    )
    replicates = _positive_integer(
        technical_replicates, "Technical replicates"
    )
    return strains * treatments * replicates


def calculate_number_of_plates(total_wells, wells_per_plate):
    """Calculate the number of plates needed."""

    wells = _positive_integer(total_wells, "Total wells")
    plate_capacity = _positive_integer(wells_per_plate, "Wells per plate")
    return math.ceil(wells / plate_capacity)


def calculate_group_master_mix(
    nucleic_acids,
    number_of_wells,
    jetprime_ratio=2,
    excess_percent=10,
    buffer_per_reaction_ul=0,
    target_total_acid_ng=None,
    empty_vector_concentration=None
):
    """Calculate one treatment's shared master mix."""

    preparation_wells = calculate_preparation_wells(
        number_of_wells,
        excess_percent
    )
    topped_up_acids = list(nucleic_acids)
    total_amount_ng = calculate_total_nucleic_acid(topped_up_acids)

    if target_total_acid_ng is not None:
        target_total_acid_ng = _finite_number(
            target_total_acid_ng, "Target total nucleic acid"
        )
        if target_total_acid_ng < 0:
            raise ValueError(
                "Target total nucleic acid cannot be negative."
            )

        if total_amount_ng < target_total_acid_ng:
            if empty_vector_concentration is None:
                raise ValueError(
                    "Enter the empty-vector stock concentration to top up "
                    "the nucleic-acid amount."
                )
            empty_vector_concentration = _finite_number(
                empty_vector_concentration,
                "Empty-vector stock concentration"
            )
            if empty_vector_concentration <= 0:
                raise ValueError(
                    "Empty-vector stock concentration must be greater than zero."
                )

            topped_up_acids.append({
                "name": "Empty Vector (pGEM)",
                "amount_per_well_ng": (
                    target_total_acid_ng - total_amount_ng
                ),
                "stock_concentration_ng_per_ul": empty_vector_concentration
            })
            total_amount_ng = target_total_acid_ng

    results = []

    for nucleic_acid in topped_up_acids:
        amount_per_well = _finite_number(
            nucleic_acid["amount_per_well_ng"],
            "Nucleic-acid amount"
        )
        concentration = _finite_number(
            nucleic_acid["stock_concentration_ng_per_ul"],
            "Stock concentration"
        )
        volume_per_well = calculate_nucleic_acid_volume(
            amount_per_well,
            concentration
        )
        results.append({
            "name": nucleic_acid["name"],
            "amount_per_well_ng": amount_per_well,
            "stock_concentration_ng_per_ul": concentration,
            "volume_per_well_ul": volume_per_well,
            "total_volume_ul": volume_per_well * preparation_wells
        })

    jetprime_per_well = calculate_jetprime_volume(
        total_amount_ng,
        jetprime_ratio
    )
    total_jetprime = jetprime_per_well * preparation_wells
    if buffer_per_reaction_ul is None:
        buffer_per_reaction = None
        total_buffer = None
        mixture_per_reaction = None
        total_mixture = None
    else:
        buffer_per_reaction = _finite_number(
            buffer_per_reaction_ul, "Buffer volume per reaction"
        )
        if buffer_per_reaction < 0:
            raise ValueError("Buffer volume per reaction cannot be negative.")
        total_buffer = buffer_per_reaction * preparation_wells
        mixture_per_reaction = (
            sum(item["volume_per_well_ul"] for item in results)
            + jetprime_per_well
            + buffer_per_reaction
        )
        total_mixture = (
            sum(item["total_volume_ul"] for item in results)
            + total_jetprime
            + total_buffer
        )

    return {
        "preparation_wells": preparation_wells,
        "nucleic_acids": results,
        "jetprime_volume_per_well_ul": jetprime_per_well,
        "jetprime_volume_ul": total_jetprime,
        "lipofectamine_volume_per_well_ul": jetprime_per_well,
        "lipofectamine_volume_ul": total_jetprime,
        "reagent_volume_per_well_ul": jetprime_per_well,
        "reagent_volume_ul": total_jetprime,
        "buffer_volume_per_reaction_ul": buffer_per_reaction,
        "buffer_volume_ul": total_buffer,
        "transfection_mixture_volume_per_reaction_ul": mixture_per_reaction,
        "total_mixture_volume_ul": total_mixture,
        "total_nucleic_acid_ng_per_well": total_amount_ng
    }


def calculate_buffer_volume(buffer_per_reaction_ul, preparation_wells):
    """Calculate the total buffer volume for a master mix."""

    volume = _finite_number(
        buffer_per_reaction_ul, "Buffer volume per reaction"
    )
    wells = _positive_integer(preparation_wells, "Preparation reactions")
    if volume < 0:
        raise ValueError("Buffer volume per reaction cannot be negative.")
    return volume * wells

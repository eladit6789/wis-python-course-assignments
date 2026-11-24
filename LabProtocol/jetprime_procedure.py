def _segment(text, bold=False):
    return {"text": text, "bold": bold}


def _step(action, details, substeps=None):
    return {
        "action": action,
        "details": details,
        "substeps": substeps or []
    }


def _format_cell_count(count):
    return f"{count:,}"


def _format_volume(value):
    return f"{value:.10f}".rstrip("0").rstrip(".")


def _method_name(protocol, manufacturer_settings):
    return (
        protocol.get("method_name")
        or manufacturer_settings.get("method_name")
        or manufacturer_settings.get("reagent_name")
        or protocol.get("protocol_name")
        or ""
    )


def build_jetprime_procedure(protocol, manufacturer_settings):
    """Build ordered, source-grounded procedure content for the Word renderer."""
    culture_format = protocol["culture_format"]
    culture_label = protocol["culture_format_settings"]["label"]
    manufacturer_protocol = manufacturer_settings["manufacturer_protocol"]
    seeding = manufacturer_protocol["cell_seeding"].get(culture_format)
    dna_protocol = manufacturer_protocol["dna_transfection"]
    confluency = manufacturer_settings["recommended_confluency"]
    method_name = _method_name(protocol, manufacturer_settings)
    is_lipofectamine = "Lipofectamine" in method_name
    reagent_name = (
        manufacturer_settings.get("reagent_name")
        or ("Lipofectamine 2000" if is_lipofectamine else "JetPRIME")
    )
    procedures = []

    if seeding is None:
        seed_details = [
            _segment(
                f"The manufacturer short protocol does not specify cells per "
                f"vessel or growth-medium volume for {culture_label}. "
                "Those seeding values are not configured in LabProtocol."
            )
        ]
    else:
        seed_details = [
            _segment("Day 0: seed each culture vessel with "),
            _segment(
                f'{_format_cell_count(seeding["minimum_cells_per_vessel"])}–'
                f'{_format_cell_count(seeding["maximum_cells_per_vessel"])} '
                "cells",
                True
            )
        ]
        if seeding["medium_volume_ml_per_vessel"] is None:
            seed_details.append(_segment(
                "; the source does not specify growth-medium volume."
            ))
        else:
            seed_details.append(_segment(
                f' in {seeding["medium_volume_ml_per_vessel"]:g} mL '
                "growth medium (the volume during transfection)."
            ))

    seed_substeps = [
        [
            _segment("On day 1, transfect at "),
            _segment(confluency, True),
            _segment(" confluency.")
        ]
    ]
    if dna_protocol["serum_during_transfection"] == "optional":
        seed_substeps.append([
            _segment(
                "The complexes may be added directly to culture medium with "
                "or without serum or antibiotics."
            )
        ])
    elif dna_protocol["serum_during_transfection"]:
        seed_substeps.append([
            _segment(
                "Keep serum-containing medium present during transfection."
            )
        ])
    procedures.append(_step("Seed cells", seed_details, seed_substeps))

    dna_substeps = [
        [_segment("Prepare a separate mixture for each treatment.")]
    ]
    ready_dilutions = []
    for config in protocol["treatment_configs"]:
        acids = config["master_mix"]["nucleic_acids"]
        if not acids:
            dna_substeps.append([
                _segment(
                    f'No nucleic-acid component is entered for '
                    f'{config["treatment"]}; a nucleic-acid dilution cannot be '
                    "prepared from this configuration.",
                    True
                )
            ])
        elif config["master_mix"]["buffer_volume_ul"] is None:
            dna_substeps.append([
                _segment(
                    f'{config["treatment"]}: the selected format has no '
                    "verified buffer volume. Do not prepare this dilution "
                    "until the buffer amount is specified.",
                    True
                )
            ])
        else:
            ready_dilutions.append(config)
            master_mix = config["master_mix"]
            acid_segments = []
            for acid_index, acid in enumerate(master_mix["nucleic_acids"]):
                if acid_index:
                    acid_segments.append(_segment(", "))
                acid_segments.extend([
                    _segment(acid["name"]),
                    _segment(
                        f' {_format_volume(acid["total_volume_ul"])} µL',
                        True
                    )
                ])

            if is_lipofectamine:
                half_buffer_volume = master_mix["buffer_volume_ul"] / 2
                dna_segments = [
                    _segment(
                        f'Dilute DNA: {config["treatment"]}: add the total '
                        "DNA volume(s) "
                    ),
                    *acid_segments,
                    _segment(" to "),
                    _segment(
                        f'{_format_volume(half_buffer_volume)} µL',
                        True
                    ),
                    _segment(f' of {dna_protocol["buffer_name"]}.')
                ]
            else:
                dna_segments = [
                    _segment(
                        f'{config["treatment"]}: add the total nucleic acid '
                        "volume(s) "
                    ),
                    *acid_segments,
                    _segment(" to "),
                    _segment(
                        f'{_format_volume(master_mix["buffer_volume_ul"])} µL',
                        True
                    ),
                    _segment(f' {dna_protocol["buffer_name"]}.')
                ]
            dna_substeps.append(dna_segments)
    if ready_dilutions:
        if is_lipofectamine:
            dna_substeps.append([
                _segment(
                    f'Dilute DNA and reagent separately in '
                    f'{dna_protocol["buffer_name"]}; use equal diluent '
                    "volumes for the two tubes."
                )
            ])
            format_settings = protocol["culture_format_settings"]
            optimization_volumes = format_settings.get(
                "optimization_reagent_volumes_ul"
            )
            if optimization_volumes:
                wells_per_condition = format_settings.get(
                    "optimization_wells_per_condition"
                )
                dna_substeps.append([
                    _segment(
                        "For cell-type optimization, the source lists four "
                        f'{reagent_name} amounts per condition: '
                        f'{", ".join(str(value) for value in optimization_volumes)} '
                        "µL. Prepare these as separate conditions. The source "
                        f'standard mix supports {wells_per_condition} well(s) '
                        "per condition; calculations here scale to the entered "
                        "well count and preparation excess."
                    )
                ])
        if dna_protocol["dna_dilution_vortex_seconds"] is not None:
            dna_substeps.append([
                _segment(
                    f'For each nucleic-acid dilution, vortex for '
                    f'{dna_protocol["dna_dilution_vortex_seconds"]} seconds, '
                    "then spin down."
                )
            ])
    dna_substeps.append([
        _segment(
            "These detailed steps apply to nucleic-acid transfection; use the "
            "manufacturer's complete protocol for siRNA-only or nucleic-acid/siRNA "
            "co-transfection."
        )
    ])
    procedures.append(_step(
        "Prepare nucleic acid dilutions",
        [
            _segment(
                "Keep treatment dilutions separate and use the total "
                "volumes shown in the reagent tables, including the "
                "preparation excess."
            )
        ],
        dna_substeps
    ))

    complex_substeps = []
    for config in ready_dilutions:
        master_mix = config["master_mix"]
        reagent_volume = (
            master_mix.get("reagent_volume_ul")
            or master_mix.get("lipofectamine_volume_ul")
            or master_mix.get("jetprime_volume_ul")
        )
        if is_lipofectamine:
            half_buffer_volume = master_mix["buffer_volume_ul"] / 2
            complex_substeps.append([
                _segment(
                    f'Dilute Reagent: {config["treatment"]}: add '
                ),
                _segment(
                    f'{_format_volume(reagent_volume)} µL',
                    True
                ),
                _segment(
                    f' of {reagent_name} to '
                ),
                _segment(
                    f'{_format_volume(half_buffer_volume)} µL',
                    True
                ),
                _segment(
                    f' of {dna_protocol["buffer_name"]} in a separate tube.'
                )
            ])
            complex_substeps.append([
                _segment(
                    f'Combine the diluted DNA and diluted reagent, and '
                    f'incubate for {dna_protocol["complex_incubation_minutes"]} '
                    f'minutes at '
                    f'{dna_protocol["complex_incubation_temperature"]}.'
                )
            ])
        else:
            complex_substeps.append([
                _segment(
                    f'{config["treatment"]}: add '
                ),
                _segment(
                    f'{_format_volume(reagent_volume)} µL',
                    True
                ),
                _segment(
                    f' {reagent_name} to its nucleic-acid dilution.'
                )
            ])
    if ready_dilutions and not is_lipofectamine:
        complex_substeps.extend([
            [
                _segment(
                    f'Vortex each mixture for '
                    f'{dna_protocol["complex_vortex_seconds"]} second, '
                    "then spin down."
                )
            ],
            [
                _segment("Incubate for "),
                _segment(
                    f'{dna_protocol["complex_incubation_minutes"]} minutes at '
                    f'{dna_protocol["complex_incubation_temperature"]}.',
                    True
                )
            ]
        ])
    elif not ready_dilutions:
        complex_substeps.append([
            _segment(
                "No complete nucleic-acid-buffer dilution is available; do not "
                "prepare a complex from this configuration.",
                True
            )
        ])
    procedures.append(_step(
        "Form transfection complexes",
        [
            _segment(
                "Follow the same order for each treatment tube."
            )
        ],
        complex_substeps
    ))

    if ready_dilutions:
        add_cell_details = [
            _segment(
                "Distribute each prepared mix only to wells assigned to its "
                "treatment."
            )
        ]
        if dna_protocol.get("medium_change_required") is False:
            add_cell_details.append(_segment(
                " A medium change or removal of complexes after transfection "
                "is not required."
            ))
        add_cell_substeps = []
        for config in ready_dilutions:
            transfection_volume = protocol[
                "culture_format_settings"
            ].get("transfection_volume_per_well_ul")
            if transfection_volume is None:
                transfection_volume = config["master_mix"][
                    "transfection_mixture_volume_per_reaction_ul"
                ]
            add_cell_substeps.append([
                _segment(f'{config["treatment"]}: add '),
                _segment(f"{transfection_volume:g} µL", True),
                _segment(
                    " of prepared mixture to each assigned well across "
                    "all strains receiving this treatment."
                )
            ])
    else:
        add_cell_details = [
            _segment(
                "No complete transfection mixture is available in this "
                "configuration; do not add a complex to cells.",
                True
            )
        ]
        add_cell_substeps = []
    procedures.append(_step(
        "Add complexes to cells", add_cell_details, add_cell_substeps
    ))

    minimum_hours = dna_protocol["cell_incubation_minimum_hours"]
    maximum_hours = dna_protocol["cell_incubation_maximum_hours"]
    selected_hours = protocol["incubation_time_hours"]
    if selected_hours is None:
        if minimum_hours is not None and maximum_hours is not None:
            incubation_details = [
                _segment("Incubate for "),
                _segment(f"{minimum_hours}–{maximum_hours} hours", True),
                _segment(" before analysis.")
            ]
            if is_lipofectamine:
                incubation_details.append(_segment(
                    " The manufacturer specifies 37 °C; the app's selected "
                    f'settings are {protocol["temperature_celsius"]:g} °C '
                    f'and {protocol["co2_percent"]:g}% CO₂, with CO₂ not '
                    "specified by the source."
                ))
            else:
                incubation_details.append(_segment(
                    " Use the selected settings of "
                    f'{protocol["temperature_celsius"]:g} °C and '
                    f'{protocol["co2_percent"]:g}% CO₂; temperature and CO₂ '
                    "are not specified by the manufacturer short protocol."
                ))
        else:
            incubation_details = [
                _segment(
                    "The post-transfection incubation duration is not "
                    "specified by the manufacturer short protocol. Use the "
                    "selected settings of "
                    f'{protocol["temperature_celsius"]:g} °C and '
                    f'{protocol["co2_percent"]:g}% CO₂; temperature and CO₂ '
                    "are not specified by the manufacturer short protocol."
                )
            ]
    else:
        incubation_details = [
            _segment("Incubate for "),
            _segment(f"{selected_hours:g} hours", True),
            _segment(" at "),
            _segment(
                f'{protocol["temperature_celsius"]:g} °C and '
                f'{protocol["co2_percent"]:g}% CO₂',
                True
            ),
            _segment(" (user-selected duration; ")
        ]
        if minimum_hours is not None and maximum_hours is not None:
            incubation_details.append(_segment(
                f"manufacturer duration is {minimum_hours}–{maximum_hours} "
                "hours)."
            ))
        else:
            incubation_details.append(_segment(
                "manufacturer duration is not specified)."
            ))
        if (
            minimum_hours is not None
            and maximum_hours is not None
            and not minimum_hours <= selected_hours <= maximum_hours
        ):
            incubation_details.append(
                _segment(
                    " This selected duration is outside the manufacturer's "
                    "stated range.",
                    True
                )
            )
    procedures.append(_step("Incubate cells", incubation_details))

    return procedures

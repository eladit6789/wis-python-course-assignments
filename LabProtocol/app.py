import io
import json
import math
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

from hbs_calculations import calculate_hbs_master_mix
from hbs_procedure import build_hbs_procedure
from jetprime_procedure import build_jetprime_procedure
from protocol_document import create_protocol_document
from jetprime_calculations import (
    calculate_group_master_mix,
    calculate_number_of_plates
)
from plate_layout import build_plate_layout

app = Flask(__name__)

METHOD_TEMPLATE_FILES = {
    "jetprime": "jetprime_template.json",
    "lipofectamine": "lipofectamine_template.json",
    "hbs": "hbs_template.json"
}


def _load_method_template(method_id):
    template_name = METHOD_TEMPLATE_FILES.get(method_id)
    if template_name is None:
        raise ValueError("Unknown transfection method.")
    with Path(__file__).with_name(template_name).open(
        encoding="utf-8"
    ) as template_file:
        return json.load(template_file)


def _template_float(value, fallback, label):
    if value is None:
        value = fallback
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} in the method template must be a number.")
    if not math.isfinite(number):
        raise ValueError(f"{label} in the method template must be finite.")
    return number


def _read_experiment_settings(defaults):
    strains = [value.strip() for value in request.form.getlist("strains")]
    treatments = [
        value.strip() for value in request.form.getlist("treatments")
    ]

    if not strains or any(not strain for strain in strains):
        raise ValueError("Enter at least one cell strain; do not leave a strain blank.")
    if not treatments or any(not treatment for treatment in treatments):
        raise ValueError(
            "Enter at least one treatment; do not leave a treatment blank."
        )

    replicate_value = request.form.get(
        "technical_replicates",
        str(defaults["technical_replicates"])
    ).strip()
    try:
        technical_replicates = int(replicate_value)
    except ValueError:
        raise ValueError("Technical replicates must be a whole number of at least 1.")
    if technical_replicates < 1:
        raise ValueError("Technical replicates must be a whole number of at least 1.")

    return strains, treatments, technical_replicates


def _read_calculation_setting(name, label, default, allow_zero):
    value = request.form.get(name, str(default)).strip()
    try:
        number = float(value)
    except ValueError:
        raise ValueError(f"{label} must be a number.")

    if not math.isfinite(number):
        raise ValueError(f"{label} must be a finite number.")
    is_invalid = number < 0 if allow_zero else number <= 0
    if is_invalid:
        if allow_zero:
            raise ValueError(f"{label} cannot be negative.")
        raise ValueError(f"{label} must be greater than zero.")

    return number


def _read_optional_positive_number(name, label):
    value = request.form.get(name, "").strip()
    if not value:
        return None

    try:
        number = float(value)
    except ValueError:
        raise ValueError(f"{label} must be a number.")
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{label} must be a finite number greater than zero.")
    return number


def _read_optional_nonnegative_number(name, label):
    value = request.form.get(name, "").strip()
    if not value:
        return None

    try:
        number = float(value)
    except ValueError:
        raise ValueError(f"{label} must be a number.")
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} cannot be negative.")
    return number


def _read_incubation_settings(defaults):
    incubation_time_hours = _read_optional_positive_number(
        "incubation_time_hours", "Incubation time"
    )
    temperature_celsius = _read_calculation_setting(
        "temperature_celsius",
        "Temperature",
        defaults["temperature_celsius"],
        False
    )
    co2_percent = _read_calculation_setting(
        "co2_percent",
        "CO2 concentration",
        defaults["co2_percent"],
        True
    )
    if co2_percent > 100:
        raise ValueError("CO2 concentration must be between 0 and 100%.")
    return incubation_time_hours, temperature_celsius, co2_percent


def _read_protocol_metadata(default_protocol_name):
    protocol_name = request.form.get(
        "protocol_name", default_protocol_name
    ).strip()
    if not protocol_name:
        raise ValueError("Protocol name cannot be blank.")

    experimental_date = request.form.get("experimental_date", "").strip()
    if experimental_date:
        try:
            datetime.strptime(experimental_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Enter the experimental date using the date picker.")

    return protocol_name, experimental_date


def _read_treatment_nucleic_acids(treatment_index, treatment):
    names = request.form.getlist(f"acid_name_{treatment_index}")
    amounts = request.form.getlist(f"acid_amount_{treatment_index}")
    concentrations = request.form.getlist(
        f"acid_concentration_{treatment_index}"
    )
    row_count = max(len(names), len(amounts), len(concentrations))

    nucleic_acids = []
    for row_index in range(row_count):
        name = names[row_index].strip() if row_index < len(names) else ""
        amount = amounts[row_index].strip() if row_index < len(amounts) else ""
        concentration = (
            concentrations[row_index].strip()
            if row_index < len(concentrations)
            else ""
        )
        if not name and not amount and not concentration:
            continue
        if name and amount and not concentration:
            raise ValueError(
                f"Treatment '{treatment}': enter the original stock "
                f"concentration for {name} in ng/µL before generating "
                "the protocol."
            )
        if not name or not amount or not concentration:
            raise ValueError(
                f"Treatment '{treatment}': complete every nucleic-acid row "
                "or remove the empty row."
            )

        try:
            amount_value = float(amount)
            concentration_value = float(concentration)
        except ValueError:
            raise ValueError(
                f"Treatment '{treatment}': nucleic-acid amount and stock "
                "concentration must be numbers."
            )

        if not math.isfinite(amount_value) or amount_value < 0:
            raise ValueError(
                f"Treatment '{treatment}': nucleic-acid amount cannot be negative."
            )
        if not math.isfinite(concentration_value) or concentration_value <= 0:
            raise ValueError(
                f"Treatment '{treatment}': stock concentration must be "
                "greater than zero."
            )

        nucleic_acids.append({
            "name": name,
            "amount_per_well_ng": amount_value,
            "stock_concentration_ng_per_ul": concentration_value
        })

    return nucleic_acids


def _read_group_replicates(group_count, default_replicates):
    group_replicates = []
    for group_index in range(group_count):
        value = request.form.get(
            f"group_replicates_{group_index}", str(default_replicates)
        ).strip()
        try:
            replicates = int(value)
        except ValueError:
            raise ValueError(
                f"Group {group_index + 1}: number of wells must be a whole "
                "number of at least 1."
            )
        if replicates < 1:
            raise ValueError(
                f"Group {group_index + 1}: number of wells must be a whole "
                "number of at least 1."
            )
        group_replicates.append(replicates)
    return group_replicates


def _build_experimental_groups(strains, treatments, group_replicates=None):
    group_replicates = group_replicates or []
    return [
        {
            "strain": strain,
            "treatment": treatment,
            "technical_replicates": (
                group_replicates[group_index]
                if group_index < len(group_replicates)
                else None
            )
        }
        for group_index, (strain, treatment) in enumerate(
            (strain, treatment)
            for strain in strains
            for treatment in treatments
        )
    ]


def _empty_nucleic_acid_row():
    return {
        "name": "",
        "amount_per_well_ng": "",
        "stock_concentration_ng_per_ul": ""
    }


def _initial_nucleic_acid_rows(method_id, treatment):
    if method_id != "hbs":
        return [_empty_nucleic_acid_row()]
    return [
        {"name": "Firefly (control)", "amount_per_well_ng": 50,
         "stock_concentration_ng_per_ul": 50},
        {"name": f"Renilla ({treatment})", "amount_per_well_ng": 30,
         "stock_concentration_ng_per_ul": ""},
        {"name": "GFP", "amount_per_well_ng": 10,
         "stock_concentration_ng_per_ul": 25}
    ]


def _culture_unit_count_label(count, culture_format_settings):
    unit = culture_format_settings["count_unit"]
    if count == 1:
        unit = {"plates": "plate", "dishes": "dish"}.get(
            unit, unit.rstrip("s")
        )
    return f"{count} {unit}"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/new-protocol")
def new_protocol():
    return render_template("new_protocol.html")


@app.route("/jetprime", methods=["GET", "POST"])
def jetprime():
    return transfection("jetprime")


@app.route("/lipofectamine", methods=["GET", "POST"])
def lipofectamine():
    return transfection("lipofectamine")


@app.route("/transfection/<method_id>", methods=["GET", "POST"])
def transfection(method_id):
    try:
        PROTOCOL_TEMPLATE = _load_method_template(method_id)
    except ValueError as exc:
        return str(exc), 404

    CULTURE_FORMATS = (
        PROTOCOL_TEMPLATE["manufacturer_settings"]["culture_formats"]
    )
    manufacturer_settings = PROTOCOL_TEMPLATE["manufacturer_settings"]
    manufacturer_protocol = manufacturer_settings["manufacturer_protocol"]
    dna_transfection_settings = manufacturer_protocol["dna_transfection"]
    DEFAULTS = dict(PROTOCOL_TEMPLATE["defaults"])
    reagent_name = (
        manufacturer_settings.get("reagent_name")
        or ("JetPRIME" if method_id == "jetprime" else "Transfection reagent")
    )
    ratio_name = "reagent_ratio" if method_id != "jetprime" else "jetprime_ratio"
    default_ratio_value = DEFAULTS.get(ratio_name)
    if default_ratio_value is None:
        default_ratio_value = DEFAULTS.get("lipofectamine_ratio")
    if default_ratio_value is None:
        default_ratio_value = DEFAULTS.get("jetprime_ratio")
    default_ratio = _template_float(
        default_ratio_value, 2, f"{reagent_name} ratio"
    )
    DEFAULTS["preparation_excess_percent"] = _template_float(
        DEFAULTS.get("preparation_excess_percent"),
        10,
        "Preparation excess"
    )
    DEFAULTS["temperature_celsius"] = _template_float(
        DEFAULTS.get("temperature_celsius"), 37, "Temperature"
    )
    DEFAULTS["co2_percent"] = _template_float(
        DEFAULTS.get("co2_percent"), 5, "CO2 concentration"
    )
    incubation_default = DEFAULTS.get("incubation_time_hours")
    DEFAULTS["incubation_time_hours"] = (
        None
        if incubation_default is None
        else _template_float(incubation_default, None, "Incubation time")
    )

    submitted_strains = []
    submitted_treatments = []
    experimental_groups = []
    treatment_configs = []
    technical_replicates = DEFAULTS["technical_replicates"]
    group_replicate_values = []
    total_wells = 0
    setup_complete = False
    calculations_complete = False
    jetprime_ratio = default_ratio
    preparation_excess_percent = DEFAULTS["preparation_excess_percent"]
    target_total_acid_ng = 1000 if method_id == "hbs" else None
    empty_vector_concentration = 500 if method_id == "hbs" else None
    incubation_time_hours = DEFAULTS["incubation_time_hours"]
    temperature_celsius = DEFAULTS["temperature_celsius"]
    co2_percent = DEFAULTS["co2_percent"]
    protocol_name = PROTOCOL_TEMPLATE["protocol_name"]
    experimental_date = ""
    culture_format = ""
    culture_format_settings = None
    culture_unit_count = 0
    protocol_generated = False
    error_message = None

    if request.method == "POST":
        stage = request.form.get("action") or request.form.get("stage", "setup")
        try:
            (
                submitted_strains,
                submitted_treatments,
                technical_replicates
            ) = _read_experiment_settings(DEFAULTS)
            culture_format = request.form.get("culture_format", "").strip()
            if culture_format not in CULTURE_FORMATS:
                raise ValueError("Select a valid culture format.")
            culture_format_settings = CULTURE_FORMATS[culture_format]
            setup_complete = True
        except ValueError as exc:
            error_message = str(exc)
            submitted_strains = [
                value.strip() for value in request.form.getlist("strains")
            ]
            submitted_treatments = [
                value.strip() for value in request.form.getlist("treatments")
            ]
            technical_replicates = request.form.get(
                "technical_replicates", 1
            )
            culture_format = request.form.get("culture_format", "").strip()

        if setup_complete and stage == "edit_setup":
            setup_complete = False
        elif setup_complete:
            group_count = len(submitted_strains) * len(submitted_treatments)
            if stage == "setup":
                group_replicates = [technical_replicates] * group_count
                group_replicate_values = [
                    str(technical_replicates)
                ] * group_count
            else:
                group_replicate_values = [
                    request.form.get(
                        f"group_replicates_{group_index}",
                        str(technical_replicates)
                    )
                    for group_index in range(group_count)
                ]
                try:
                    group_replicates = _read_group_replicates(
                        group_count, technical_replicates
                    )
                    group_replicate_values = [
                        str(value) for value in group_replicates
                    ]
                except ValueError as exc:
                    error_message = str(exc)
                    group_replicates = [technical_replicates] * group_count

            experimental_groups = _build_experimental_groups(
                submitted_strains, submitted_treatments, group_replicates
            )
            total_wells = sum(group_replicates)
            culture_unit_count = calculate_number_of_plates(
                total_wells,
                culture_format_settings["vessels_per_unit"]
            )

            if error_message:
                treatment_configs = [
                    {
                        "treatment": treatment,
                        "number_of_wells": sum(
                            group["technical_replicates"]
                            for group in experimental_groups
                            if group["treatment"] == treatment
                        ),
                        "nucleic_acids": [_empty_nucleic_acid_row()]
                    }
                    for treatment in submitted_treatments
                ]
            elif stage == "setup":
                treatment_configs = [
                    {
                        "treatment": treatment,
                        "number_of_wells": sum(
                            group["technical_replicates"]
                            for group in experimental_groups
                            if group["treatment"] == treatment
                        ),
                        "nucleic_acids": _initial_nucleic_acid_rows(
                            method_id, treatment
                        )
                    }
                    for treatment in submitted_treatments
                ]
            elif stage in (
                "save_nucleic_acids",
                "generate_protocol",
                "download_docx",
                "edit_details"
            ):
                ratio_value = request.form.get(
                    ratio_name,
                    request.form.get("jetprime_ratio", str(default_ratio))
                )
                excess_value = request.form.get(
                    "preparation_excess_percent",
                    str(DEFAULTS["preparation_excess_percent"])
                )
                target_total_acid_value = request.form.get(
                    "target_total_acid_ng", ""
                )
                empty_vector_concentration_value = request.form.get(
                    "empty_vector_concentration", ""
                )
                incubation_time_value = request.form.get(
                    "incubation_time_hours", ""
                )
                temperature_value = request.form.get(
                    "temperature_celsius",
                    str(DEFAULTS["temperature_celsius"])
                )
                co2_value = request.form.get(
                    "co2_percent", str(DEFAULTS["co2_percent"])
                )
                protocol_name_value = request.form.get(
                    "protocol_name", PROTOCOL_TEMPLATE["protocol_name"]
                )
                experimental_date_value = request.form.get(
                    "experimental_date", ""
                )
                try:
                    (
                        incubation_time_hours,
                        temperature_celsius,
                        co2_percent
                    ) = _read_incubation_settings(DEFAULTS)
                    (
                        protocol_name,
                        experimental_date
                    ) = _read_protocol_metadata(
                        PROTOCOL_TEMPLATE["protocol_name"]
                    )
                    if method_id != "hbs":
                        jetprime_ratio = _read_calculation_setting(
                            ratio_name,
                            f"{reagent_name} ratio",
                            default_ratio,
                            False
                        )
                    preparation_excess_percent = _read_calculation_setting(
                        "preparation_excess_percent",
                        "Preparation excess",
                        DEFAULTS["preparation_excess_percent"],
                        True
                    )
                    target_total_acid_ng = _read_optional_nonnegative_number(
                        "target_total_acid_ng",
                        "Target total nucleic acid"
                    )
                    empty_vector_concentration = (
                        _read_optional_positive_number(
                            "empty_vector_concentration",
                            "Empty-vector stock concentration"
                        )
                        if request.form.get(
                            "empty_vector_concentration", ""
                        ).strip()
                        else None
                    )
                    treatment_configs = []
                    for treatment_index, treatment in enumerate(
                        submitted_treatments
                    ):
                        treatment_wells = sum(
                            group["technical_replicates"]
                            for group in experimental_groups
                            if group["treatment"] == treatment
                        )
                        nucleic_acids = _read_treatment_nucleic_acids(
                            treatment_index, treatment
                        )
                        if method_id == "hbs":
                            master_mix = calculate_hbs_master_mix(
                                nucleic_acids, treatment_wells,
                                preparation_excess_percent, target_total_acid_ng,
                                empty_vector_concentration
                            )
                        else:
                            master_mix = calculate_group_master_mix(
                                nucleic_acids=nucleic_acids,
                                number_of_wells=treatment_wells,
                                jetprime_ratio=jetprime_ratio,
                                excess_percent=preparation_excess_percent,
                                buffer_per_reaction_ul=(
                                    culture_format_settings[
                                        "buffer_volume_per_reaction_ul"
                                    ]
                                ),
                                target_total_acid_ng=target_total_acid_ng,
                                empty_vector_concentration=(
                                    empty_vector_concentration
                                )
                            )
                        treatment_configs.append({
                            "treatment": treatment,
                            "nucleic_acids": nucleic_acids,
                            "number_of_wells": treatment_wells,
                            "master_mix": master_mix
                        })
                    calculations_complete = stage != "edit_details"
                    protocol_generated = stage in (
                        "generate_protocol",
                        "download_docx"
                    )
                except ValueError as exc:
                    error_message = str(exc)
                    jetprime_ratio = ratio_value
                    preparation_excess_percent = excess_value
                    target_total_acid_ng = (
                        target_total_acid_value.strip()
                        or None
                    )
                    empty_vector_concentration = (
                        empty_vector_concentration_value.strip()
                        or None
                    )
                    incubation_time_hours = incubation_time_value
                    temperature_celsius = temperature_value
                    co2_percent = co2_value
                    protocol_name = protocol_name_value
                    experimental_date = experimental_date_value
                    treatment_configs = []
                    for treatment_index, treatment in enumerate(
                        submitted_treatments
                    ):
                        row_names = request.form.getlist(
                            f"acid_name_{treatment_index}"
                        )
                        row_amounts = request.form.getlist(
                            f"acid_amount_{treatment_index}"
                        )
                        row_concentrations = request.form.getlist(
                            f"acid_concentration_{treatment_index}"
                        )
                        rows = []
                        for row_index in range(max(
                            len(row_names),
                            len(row_amounts),
                            len(row_concentrations)
                        )):
                            rows.append({
                                "name": (
                                    row_names[row_index]
                                    if row_index < len(row_names)
                                    else ""
                                ),
                                "amount_per_well_ng": (
                                    row_amounts[row_index]
                                    if row_index < len(row_amounts)
                                    else ""
                                ),
                                "stock_concentration_ng_per_ul": (
                                    row_concentrations[row_index]
                                    if row_index < len(row_concentrations)
                                    else ""
                                )
                            })
                        treatment_configs.append({
                            "treatment": treatment,
                            "nucleic_acids": rows or [_empty_nucleic_acid_row()]
                        })
            else:
                error_message = "Unrecognized experiment setup step."
                setup_complete = False
                experimental_groups = []
                treatment_configs = []

    if protocol_generated and calculations_complete:
        protocol_context = {
            "protocol_name": protocol_name,
            "experimental_date": experimental_date,
            "submitted_strains": submitted_strains,
            "submitted_treatments": submitted_treatments,
            "experimental_groups": experimental_groups,
            "group_replicate_values": group_replicate_values,
            "treatment_configs": treatment_configs,
            "technical_replicates": technical_replicates,
            "total_wells": total_wells,
            "culture_format": culture_format,
            "culture_format_settings": culture_format_settings,
            "culture_unit_count": culture_unit_count,
            "culture_unit_count_label": _culture_unit_count_label(
                culture_unit_count, culture_format_settings
            ),
            "jetprime_ratio": jetprime_ratio,
            "reagent_ratio": jetprime_ratio,
            "ratio_name": ratio_name,
            "reagent_name": reagent_name,
            "method_id": method_id,
            "method_name": (
                PROTOCOL_TEMPLATE["protocol_name"]
            ),
            "preparation_excess_percent": preparation_excess_percent,
            "target_total_acid_ng": target_total_acid_ng,
            "empty_vector_concentration": empty_vector_concentration,
            "incubation_time_hours": incubation_time_hours,
            "temperature_celsius": temperature_celsius,
            "co2_percent": co2_percent,
            "manufacturer_settings": manufacturer_settings,
            "manufacturer_protocol_source_label": manufacturer_protocol[
                "source_label"
            ],
            "manufacturer_incubation_minimum_hours": (
                dna_transfection_settings["cell_incubation_minimum_hours"]
            ),
            "manufacturer_incubation_maximum_hours": (
                dna_transfection_settings["cell_incubation_maximum_hours"]
            ),
            "verified_procedure": PROTOCOL_TEMPLATE[
                "manufacturer_verified_procedure"
            ],
            "procedure_confirmations": PROTOCOL_TEMPLATE[
                "manufacturer_procedure_confirmations"
            ]
        }
        layout_settings = culture_format_settings["layout"]
        protocol_context["plate_layouts"] = build_plate_layout(
            experimental_groups,
            rows=layout_settings["rows"],
            columns=layout_settings["columns"],
            container_label=layout_settings["container_label"],
            position_prefix=layout_settings.get("position_prefix")
        )
        protocol_context["procedure_steps"] = (
            build_hbs_procedure(protocol_context)
            if method_id == "hbs"
            else build_jetprime_procedure(protocol_context, manufacturer_settings)
        )
        protocol_context["procedure_source"] = {
            "label": manufacturer_protocol["source_label"],
            "status": manufacturer_protocol["source_status"]
        }
        if stage == "download_docx":
            document = create_protocol_document(protocol_context)
            output = io.BytesIO()
            document.save(output)
            output.seek(0)
            filename = secure_filename(protocol_name) or "jetprime_protocol"
            return send_file(
                output,
                as_attachment=True,
                download_name=f"{filename}.docx",
                mimetype=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                )
            )
        return render_template("protocol.html", **protocol_context)

    return render_template(
        "experiment_setup.html",
        submitted_strains=submitted_strains,
        submitted_treatments=submitted_treatments,
        experimental_groups=experimental_groups,
        group_replicate_values=group_replicate_values,
        treatment_configs=treatment_configs,
        technical_replicates=technical_replicates,
        total_wells=total_wells,
        setup_complete=setup_complete,
        calculations_complete=calculations_complete,
        jetprime_ratio=jetprime_ratio,
        reagent_ratio=jetprime_ratio,
        reagent_name=reagent_name,
        method_id=method_id,
        method_name=PROTOCOL_TEMPLATE["protocol_name"],
        ratio_name=ratio_name,
        preparation_excess_percent=preparation_excess_percent,
        target_total_acid_ng=target_total_acid_ng,
        empty_vector_concentration=empty_vector_concentration,
        incubation_time_hours=incubation_time_hours,
        temperature_celsius=temperature_celsius,
        co2_percent=co2_percent,
        protocol_name=protocol_name,
        experimental_date=experimental_date,
        culture_formats=CULTURE_FORMATS,
        manufacturer_settings=manufacturer_settings,
        manufacturer_protocol_source_label=manufacturer_protocol["source_label"],
        manufacturer_incubation_minimum_hours=(
            dna_transfection_settings["cell_incubation_minimum_hours"]
        ),
        manufacturer_incubation_maximum_hours=(
            dna_transfection_settings["cell_incubation_maximum_hours"]
        ),
        culture_format=culture_format,
        culture_format_settings=culture_format_settings,
        culture_unit_count=culture_unit_count,
        error_message=error_message
    )


if __name__ == "__main__":
    app.run(debug=True)

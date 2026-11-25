from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Inches, Pt, RGBColor


_TABLE_BORDER_COLOR = "000000"
_BLACK = RGBColor(0, 0, 0)


def _set_cell_margins(cell, margin=65):
    properties = cell._tc.get_or_add_tcPr()
    margins = properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for edge in ("top", "start", "bottom", "end"):
        element = margins.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            margins.append(element)
        element.set(qn("w:w"), str(margin))
        element.set(qn("w:type"), "dxa")


def _set_table_borders(table, color=_TABLE_BORDER_COLOR):
    properties = table._tbl.tblPr
    borders = properties.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        properties.append(borders)
    else:
        for child in list(borders):
            borders.remove(child)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "4")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), color)
        borders.append(border)


def _format_table(
    table, widths, has_header=False, border_color=_TABLE_BORDER_COLOR,
    cell_margin=65, font_size=8
):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    table._tbl.tblPr.append(layout)
    _set_table_borders(table, border_color)

    for column, width in zip(table.columns, widths):
        column.width = width
    for row_index, row in enumerate(table.rows):
        row_properties = row._tr.get_or_add_trPr()
        if row_index == 0 and has_header:
            repeat_header = OxmlElement("w:tblHeader")
            repeat_header.set(qn("w:val"), "true")
            row_properties.append(repeat_header)
        for column_index, cell in enumerate(row.cells):
            cell.width = widths[column_index]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_cell_margins(cell, cell_margin)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.space_before = Pt(0)
            if has_header and row_index == 0:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                if has_header and column_index > 0:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for run in paragraph.runs:
                run.font.name = "Arial"
                run.font.size = Pt(font_size)
                run.font.color.rgb = _BLACK
                if has_header and row_index == 0:
                    run.bold = True


def _format_volume(volume_ul):
    if volume_ul is None:
        return "Requires confirmation"
    value = f"{volume_ul:.3f}".rstrip("0").rstrip(".")
    return f"{value} µL"


def _format_number(value):
    return f"{value:.10f}".rstrip("0").rstrip(".")


def _format_amount(amount):
    return f"{amount:g}"


def _format_stock_concentration(concentration):
    if concentration is None:
        return "Requires confirmation"
    return _format_amount(concentration)


def _add_experimental_overview(document, protocol, available_width):
    replicate_summary = "; ".join(
        f'{group["strain"]} / {group["treatment"]}: '
        f'{group["technical_replicates"]}'
        for group in protocol["experimental_groups"]
    )
    rows = (
        ("Cell strains", ", ".join(protocol["submitted_strains"])),
        ("Treatments", ", ".join(protocol["submitted_treatments"])),
        ("Culture format", protocol["culture_format_settings"]["label"]),
        ("Technical replicates per group", replicate_summary),
        ("Experimental wells", str(protocol["total_wells"])),
        ("Plates or dishes required", protocol["culture_unit_count_label"])
    )
    table = document.add_table(rows=0, cols=2)
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value
        for run in cells[0].paragraphs[0].runs:
            run.bold = True
    _format_table(
        table,
        [Emu(int(available_width * 0.30)), Emu(int(available_width * 0.70))]
    )


def _add_layout_cell(cell, well, font_size):
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1

    position = paragraph.add_run(well["position"])
    position.bold = True
    lines = [position]
    if well["strain"] is not None:
        for text in (
            well["strain"],
            well["treatment"],
            f'Rep {well["replicate"]}'
        ):
            lines[-1].add_break()
            line = paragraph.add_run(text)
            lines.append(line)
    else:
        lines[-1].add_break()
        empty = paragraph.add_run("Empty")
        lines.append(empty)
    for run in lines:
        run.font.name = "Arial"
        run.font.size = Pt(font_size)
        run.font.color.rgb = _BLACK


def _add_plate_layout(document, plate_layouts, available_width):
    for plate in plate_layouts:
        document.add_heading(plate["label"], level=2)
        column_count = plate["column_count"]
        panel_width = min(column_count, 6)
        font_size = 7.5 if column_count > 4 else 8
        for first_column in range(0, column_count, panel_width):
            last_column = min(first_column + panel_width, column_count)
            if column_count > panel_width:
                panel_label = document.add_paragraph()
                panel_label.paragraph_format.space_before = Pt(1)
                panel_label.paragraph_format.space_after = Pt(2)
                run = panel_label.add_run(
                    f"Columns {first_column + 1}–{last_column}"
                )
                run.bold = True
                run.font.size = Pt(8)
                run.font.color.rgb = _BLACK

            visible_columns = last_column - first_column
            table = document.add_table(
                rows=plate["row_count"],
                cols=visible_columns
            )
            for row_index, row in enumerate(plate["rows"]):
                for visible_column, column_index in enumerate(
                    range(first_column, last_column)
                ):
                    _add_layout_cell(
                        table.cell(row_index, visible_column),
                        row[column_index],
                        font_size
                    )
            _format_table(
                table,
                [
                    Emu(int(available_width / visible_columns))
                    for _ in range(visible_columns)
                ],
                border_color="000000",
                cell_margin=35,
                font_size=font_size
            )


def _add_reagent_table(
    document, treatment_config, preparation_excess_percent, available_width,
    reagent_name="JetPRIME", buffer_name="Buffer", is_hbs=False
):
    master_mix = treatment_config["master_mix"]
    table = document.add_table(rows=1, cols=5)
    headers = (
        "Component",
        "Stock concentration\n(ng/µL)",
        "Amount per well\n(ng)",
        "Volume per well\n(µL)",
        "Total volume to prepare\n(µL)"
    )
    for cell, text in zip(table.rows[0].cells, headers):
        cell.text = text

    nucleic_acids = master_mix["nucleic_acids"]
    for acid in nucleic_acids:
        cells = table.add_row().cells
        cells[0].text = acid["name"]
        cells[1].text = _format_stock_concentration(
            acid["stock_concentration_ng_per_ul"]
        )
        cells[2].text = _format_amount(acid["amount_per_well_ng"])
        cells[3].text = _format_volume(acid["volume_per_well_ul"])
        cells[4].text = _format_volume(acid["total_volume_ul"])

    components = (
        (
            reagent_name,
            master_mix["reagent_volume_per_well_ul"],
            master_mix["reagent_volume_ul"]
        ),
        (
            buffer_name,
            master_mix["buffer_volume_per_reaction_ul"],
            master_mix["buffer_volume_ul"]
        )
    ) if not is_hbs else (
        ("DDW", master_mix["water_per_well_ul"], master_mix["water_total_ul"]),
        ("CaCl2 (2.5 M)", master_mix["cacl2_per_well_ul"], master_mix["cacl2_total_ul"]),
        ("2x HBS", master_mix["hbs_per_well_ul"], master_mix["hbs_total_ul"])
    )
    for label, per_vessel, total in components:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = "N/A"
        cells[2].text = "N/A"
        cells[3].text = _format_volume(per_vessel)
        cells[4].text = _format_volume(total)

    column_widths = [
        Emu(int(available_width * fraction))
        for fraction in (0.20, 0.18, 0.18, 0.18, 0.26)
    ]
    _format_table(table, column_widths, has_header=True)
    for row in table.rows[1:]:
        for column_index, cell in enumerate(row.cells):
            for run in cell.paragraphs[0].runs:
                run.bold = column_index in (0, 4)

    note = document.add_paragraph()
    note.paragraph_format.space_before = Pt(2)
    note.paragraph_format.space_after = Pt(5)
    note.add_run(
        f'Prepare {_format_number(master_mix["preparation_wells"])} '
        f'reaction-equivalents; '
        f'totals include {preparation_excess_percent:g}% preparation excess.'
    )


def _add_step(document, action, details):
    paragraph = document.add_paragraph(style="List Number")
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.left_indent = Inches(0.28)
    paragraph.paragraph_format.first_line_indent = Inches(-0.2)
    action_run = paragraph.add_run(action + ": ")
    action_run.bold = True
    action_run.font.color.rgb = _BLACK
    _add_segments(paragraph, details)


def _add_segments(paragraph, segments):
    for segment in segments:
        run = paragraph.add_run(segment["text"])
        run.bold = segment["bold"]
        run.font.color.rgb = _BLACK


def _add_procedure(document, steps):
    for step in steps:
        _add_step(document, step["action"], step["details"])
        for substep in step["substeps"]:
            paragraph = document.add_paragraph(style="List Bullet")
            paragraph.paragraph_format.left_indent = Inches(0.55)
            paragraph.paragraph_format.first_line_indent = Inches(-0.16)
            paragraph.paragraph_format.space_after = Pt(3)
            paragraph.paragraph_format.keep_together = True
            _add_segments(paragraph, substep)


def create_protocol_document(protocol):
    """Render validated experiment data as a compact, mergeable protocol block."""
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.6)
    section.right_margin = Inches(0.6)

    styles = document.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(9)
    styles["Normal"].font.color.rgb = _BLACK
    styles["Normal"].paragraph_format.space_after = Pt(3)
    styles["Title"].font.name = "Arial"
    styles["Title"].font.size = Pt(18)
    styles["Title"].font.bold = True
    styles["Title"].font.color.rgb = _BLACK
    styles["Heading 1"].font.name = "Arial"
    styles["Heading 1"].font.size = Pt(14)
    styles["Heading 1"].font.bold = True
    styles["Heading 1"].font.color.rgb = _BLACK
    styles["Heading 1"].paragraph_format.space_before = Pt(10)
    styles["Heading 1"].paragraph_format.space_after = Pt(4)
    styles["Heading 1"].paragraph_format.keep_with_next = True
    styles["Heading 2"].font.name = "Arial"
    styles["Heading 2"].font.size = Pt(10)
    styles["Heading 2"].font.bold = True
    styles["Heading 2"].font.color.rgb = _BLACK
    styles["Heading 2"].paragraph_format.space_before = Pt(5)
    styles["Heading 2"].paragraph_format.space_after = Pt(2)
    styles["Heading 2"].paragraph_format.keep_with_next = True
    for style_name in ("List Number", "List Bullet"):
        styles[style_name].font.name = "Arial"
        styles[style_name].font.size = Pt(9)
        styles[style_name].font.color.rgb = _BLACK

    document.add_heading(protocol["protocol_name"], level=0)
    experimental_date = protocol.get("experimental_date")
    if experimental_date:
        date_paragraph = document.add_paragraph()
        date_paragraph.paragraph_format.space_after = Pt(12)
        date_run = date_paragraph.add_run(
            f"Experimental date: {experimental_date}"
        )
        date_run.font.name = "Arial"
        date_run.font.size = Pt(10)
        date_run.font.color.rgb = _BLACK
    available_width = (
        section.page_width - section.left_margin - section.right_margin
    )

    document.add_heading("1. Experimental Overview", level=1)
    _add_experimental_overview(document, protocol, available_width)

    document.add_heading("2. Plate Layout", level=1)
    _add_plate_layout(document, protocol["plate_layouts"], available_width)

    document.add_heading("3. Reagent Preparation", level=1)
    for mix_number, config in enumerate(protocol["treatment_configs"], start=1):
        document.add_heading(
            f'Master Mix {mix_number} – {config["treatment"]}',
            level=2
        )
        master_mix = config["master_mix"]
        if (protocol.get("method_id") != "hbs"
                and master_mix["buffer_volume_per_reaction_ul"] is None):
            warning = document.add_paragraph()
            warning.add_run("Do not use this mix until confirmed: ").bold = True
            warning.add_run(
                "the manufacturer buffer volume for the selected culture "
                "format has not been verified."
            )
        _add_reagent_table(
            document,
            config,
            protocol["preparation_excess_percent"],
            available_width,
            protocol["reagent_name"],
            protocol["culture_format_settings"].get(
                "buffer_name", "Buffer"
            ),
            protocol.get("method_id") == "hbs"
        )

    document.add_heading("4. Procedure", level=1)
    _add_procedure(document, protocol["procedure_steps"])
    if protocol.get("method_id") == "hbs":
        document.add_heading("Confirm before use", level=2)
        for confirmation in protocol["procedure_confirmations"]:
            document.add_paragraph(confirmation, style="List Bullet")
        document.add_paragraph(
            "User-selected incubation settings: "
            f'{protocol["temperature_celsius"]:g} °C, '
            f'{protocol["co2_percent"]:g}% CO₂; '
            + (f'{protocol["incubation_time_hours"]:g} hours.'
               if protocol["incubation_time_hours"] is not None
               else "duration not specified.")
        )
    source = protocol.get("procedure_source")
    if source:
        source_paragraph = document.add_paragraph()
        source_paragraph.paragraph_format.space_before = Pt(3)
        source_paragraph.paragraph_format.space_after = Pt(0)
        source_run = source_paragraph.add_run(
            f'Source: {source["label"]} (status {source["status"]}).'
        )
        source_run.italic = True
        source_run.font.size = Pt(8)
        source_run.font.color.rgb = _BLACK

    return document

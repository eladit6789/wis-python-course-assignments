from flask import Flask, render_template, request

from training.dna_composition import calculate_percentages


app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/", methods=["GET", "POST"])
def dna_calculator():
    sequence = ""
    percentages = None
    error = None

    if request.method == "POST":
        sequence = request.form.get("sequence", "")
        try:
            percentages = calculate_percentages(sequence)
        except ValueError as exc:
            error = str(exc)

    return render_template(
        "dna.html",
        sequence=sequence,
        percentages=percentages,
        error=error,
    )


if __name__ == "__main__":
    app.run(port=5001, debug=False)

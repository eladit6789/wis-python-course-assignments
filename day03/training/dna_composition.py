from pathlib import Path


def calculate_percentages(sequence):
    """Calculate the percentage of each DNA base and of CG/AT bases."""
    sequence = sequence.strip().upper()
    if not sequence:
        raise ValueError("The DNA sequence cannot be empty.")

    invalid_bases = set(sequence) - {"A", "C", "G", "T"}
    if invalid_bases:
        raise ValueError(
            f"Invalid DNA characters: {', '.join(sorted(invalid_bases))}"
        )

    sequence_length = len(sequence)
    percentages = {
        base: sequence.count(base) / sequence_length * 100
        for base in "ACGT"
    }
    percentages["CG"] = percentages["C"] + percentages["G"]
    percentages["AT"] = percentages["A"] + percentages["T"]
    return percentages


def main():
    data_file = Path(__file__).with_name("sample_dna.txt")

    try:
        sequence = data_file.read_text(encoding="utf-8")
        percentages = calculate_percentages(sequence)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Error: {error}") from error

    print(f"DNA sequence: {sequence.strip().upper()}")
    print("Nucleotide percentages:")
    for base in "ACGT":
        print(f"{base}: {percentages[base]:.2f}%")
    print(f"CG: {percentages['CG']:.2f}%")
    print(f"AT: {percentages['AT']:.2f}%")


if __name__ == "__main__":
    main()

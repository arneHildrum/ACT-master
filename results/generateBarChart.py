import os
import re
import matplotlib.pyplot as plt
import yaml


def extract_grams(value):
    """Extract numerical value from strings like '1169127.7325235016 gram'."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"[-+]?\d*\.\d+|\d+", value)
        if match:
            return float(match.group())
    return 0.0


def plot_carbon_data(directory="."):
    filenames = []
    fabrication_values = []
    operation_values = []
    packaging_values = []

    # Find and parse all .yaml files in the directory
    for file in sorted(os.listdir(directory)):
        if file.endswith((".yaml", ".yml")):
            filepath = os.path.join(directory, file)
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    data = yaml.safe_load(f)
                    total_carbon = data.get("total_carbon", {})

                    fab = extract_grams(total_carbon.get("fabrication", 0))
                    op = extract_grams(total_carbon.get("operation", 0))
                    pack = extract_grams(total_carbon.get("packaging", 0))

                    filenames.append(file)
                    fabrication_values.append(fab)
                    operation_values.append(op)
                    packaging_values.append(pack)
                except Exception as e:
                    print(f"Error reading {file}: {e}")

    if not filenames:
        print("No .yaml files found in the specified directory.")
        return

    # Create the stacked bar chart
    fig, ax = plt.subplots(figsize=(10, 6))

    # Stacking bars: operation (bottom), fabrication (middle), packaging (top)
    bar_op = ax.bar(filenames, operation_values, label="Operation", color="blue")
    bar_fab = ax.bar(
        filenames,
        fabrication_values,
        bottom=operation_values,
        label="Fabrication",
        color="red",
    )

    # Combine operation and fabrication for the bottom position of packaging
    op_plus_fab = [
        op + fab for op, fab in zip(operation_values, fabrication_values)
    ]
    bar_pack = ax.bar(
        filenames,
        packaging_values,
        bottom=op_plus_fab,
        label="Packaging",
        color="green",
    )

    # Labels and formatting
    ax.set_ylabel("Total Carbon (grams)")
    ax.set_title("Total Carbon Breakdown per File")
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    # Save and show graph
    plt.savefig("carbon_breakdown_chart.png")
    plt.show()


if __name__ == "__main__":
    plot_carbon_data()
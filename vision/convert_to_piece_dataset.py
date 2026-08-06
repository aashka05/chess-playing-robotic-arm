from pathlib import Path

# Change this path if your dataset is elsewhere
DATASET = Path("vision/data/chess_dataset_piece")

label_dirs = [
    DATASET / "train" / "labels",
    DATASET / "valid" / "labels",
    DATASET / "test" / "labels",
]

total_files = 0
total_labels = 0

for label_dir in label_dirs:
    if not label_dir.exists():
        continue

    for txt_file in label_dir.glob("*.txt"):
        total_files += 1

        new_lines = []

        with open(txt_file, "r") as f:
            for line in f:
                parts = line.strip().split()

                if len(parts) != 5:
                    continue

                parts[0] = "0"   # Change every class to "piece"

                new_lines.append(" ".join(parts))
                total_labels += 1

        with open(txt_file, "w") as f:
            f.write("\n".join(new_lines))

print(f"Done!")
print(f"Files processed : {total_files}")
print(f"Labels modified : {total_labels}")
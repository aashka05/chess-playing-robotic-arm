diff = 2.8
y_start = 50
cols = 'abcdefgh'

col_blocks = []
for col_idx in range(8):
    x = round((col_idx - 3.5) * diff, 3)
    entries = []
    for row in range(1, 9):
        y = round(y_start + (row - 1) * diff, 3)
        key = f'{cols[col_idx]}{row}'
        entries.append(f'"{key}": [{x}, {y}]')
    col_blocks.append("  " + ", ".join(entries))

output = "{\n" + ",\n\n".join(col_blocks) + "\n}"

with open('sq_dict.json', 'w') as f:
    f.write(output)
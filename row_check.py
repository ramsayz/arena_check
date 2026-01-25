row_metrics = {}

for y, text in row_text.items():
    # Robust NAV extraction (kerning-safe)
    raw_nav_tokens = re.findall(r'(?:\d[\d,\s,]{3,}\d)', text)
    nav_nums = []
    for tok in raw_nav_tokens:
        cleaned = tok.replace(" ", "")
        if re.search(r'\d,\d{3}', cleaned):
            nav_nums.append(cleaned)

    # MTD extraction (already stable)
    mtd_nums = re.findall(r'-?\d+\.\d+%', text)

    row_metrics[y] = {
        "nav_count": len(nav_nums),
        "mtd_count": len(mtd_nums),
        "nav_nums": nav_nums,
        "mtd_nums": mtd_nums
    }

nav_row_y = max(row_metrics, key=lambda y: row_metrics[y]["nav_count"])
mtd_row_y = max(row_metrics, key=lambda y: row_metrics[y]["mtd_count"])

nav_tokens = row_metrics[nav_row_y]["nav_nums"]
mtd_tokens = row_metrics[mtd_row_y]["mtd_nums"]

import re

row_metrics = {}

for y, text in row_text.items():
    raw_nav_tokens = re.findall(r'[\d,\s]{7,}', text)
    nav_nums = []

    for tok in raw_nav_tokens:
        cleaned = tok.replace(" ", "")
        if re.fullmatch(r'\d{1,3}(?:,\d{3})+', cleaned):
            nav_nums.append(cleaned)

    mtd_nums = re.findall(r'-?\d+\.\d+%', text)

    row_metrics[y] = {
        "nav_count": len(nav_nums),
        "mtd_count": len(mtd_nums),
        "nav_nums": nav_nums,
        "mtd_nums": mtd_nums
    }

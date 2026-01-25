import pdfplumber
import pandas as pd
import re
from collections import defaultdict

def extract_arena(file_path, workflow_path):

    # --------------------------------------------------
    # 1. Read workflow
    # --------------------------------------------------
    wf = pd.read_excel(workflow_path)
    wf = wf[wf["Fund Name"].str.contains("Arena", case=False, na=False)]
    wf = wf.reset_index(drop=True)
    fund_count = len(wf)

    if fund_count == 0:
        raise ValueError("Arena: No Arena funds in workflow")

    # --------------------------------------------------
    # 2. Read PDF characters
    # --------------------------------------------------
    chars = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            chars.extend(page.chars)

    if not chars:
        raise ValueError("Arena PDF: No text extracted")

    # --------------------------------------------------
    # 3. Group chars into rows
    # --------------------------------------------------
    rows = defaultdict(list)
    for c in chars:
        rows[round(c["top"], 1)].append(c)

    # --------------------------------------------------
    # 4. Merge characters into numeric tokens
    # --------------------------------------------------
    def build_tokens(row):
        row = sorted(row, key=lambda x: x["x0"])
        tokens = []
        current = [row[0]]

        for c in row[1:]:
            if c["x0"] - current[-1]["x1"] <= 2:  # tight digit spacing
                current.append(c)
            else:
                tokens.append(current)
                current = [c]

        tokens.append(current)
        return tokens

    # --------------------------------------------------
    # 5. Find NAV row
    # --------------------------------------------------
    nav_values = None

    for row in sorted(rows.values(), key=lambda r: r[0]["top"]):
        tokens = build_tokens(row)
        values = []

        for tok in tokens:
            text = "".join(c["text"] for c in tok).replace(",", "").strip()
            if "/" in text or not text.isdigit():
                continue
            values.append(float(text))

        if len(values) >= fund_count:
            nav_values = values[:fund_count]
            break

    if nav_values is None:
        raise ValueError("Arena PDF: NAV row not found")

    # --------------------------------------------------
    # 6. Find MTD row
    # --------------------------------------------------
    mtd_values = None

    for row in sorted(rows.values(), key=lambda r: r[0]["top"]):
        tokens = build_tokens(row)
        values = []

        for tok in tokens:
            text = "".join(c["text"] for c in tok).replace("%", "").strip()
            if "/" in text:
                continue
            try:
                values.append(float(text))
            except ValueError:
                continue

        if len(values) >= fund_count:
            mtd_values = values[:fund_count]
            break

    if mtd_values is None:
        raise ValueError("Arena PDF: MTD row not found")

    # --------------------------------------------------
    # 7. Output
    # --------------------------------------------------
    wf["NAV"] = nav_values
    wf["MTD"] = mtd_values
    wf["Variance"] = abs(wf["MTD"])

    return wf

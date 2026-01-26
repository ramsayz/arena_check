import pdfplumber
import pandas as pd
from collections import defaultdict

def extract_arena(file_path, workflow_path):

    # --------------------------------------------------
    # 1. Read workflow (Arena funds only)
    # --------------------------------------------------
    wf = pd.read_excel(workflow_path)
    wf = wf[wf["Fund Name"].str.contains("Arena", case=False, na=False)]
    wf = wf.reset_index(drop=True)
    fund_count = len(wf)

    if fund_count == 0:
        raise ValueError("Arena: No Arena funds found in workflow")

    # --------------------------------------------------
    # 2. Read all characters from PDF
    # --------------------------------------------------
    chars = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            chars.extend(page.chars)

    if not chars:
        raise ValueError("Arena PDF: No text extracted")

    # --------------------------------------------------
    # 3. Group characters into rows (by Y)
    # --------------------------------------------------
    rows = defaultdict(list)
    for c in chars:
        rows[round(c["top"], 1)].append(c)

    # --------------------------------------------------
    # 4. Build numeric tokens (merge digits + commas)
    # --------------------------------------------------
    def build_numeric_tokens(row):
        row = sorted(row, key=lambda x: x["x0"])
        tokens = []
        current = [row[0]]

        for c in row[1:]:
            prev = current[-1]

            # merge digits and commas regardless of spacing
            if (
                (prev["text"].isdigit() or prev["text"] == ",")
                and (c["text"].isdigit() or c["text"] == ",")
            ):
                current.append(c)
            else:
                tokens.append(current)
                current = [c]

        tokens.append(current)
        return tokens

    # --------------------------------------------------
    # 5. Extract NAV row (first valid one)
    # --------------------------------------------------
    nav_values = None

    for row in sorted(rows.values(), key=lambda r: r[0]["top"]):
        tokens = build_numeric_tokens(row)
        values = []

        for tok in tokens:
            text = "".join(c["text"] for c in tok).replace(",", "").strip()

            # skip dates or garbage
            if not text.isdigit():
                continue

            # skip date fragments like 10, 1, 2025
            if len(text) < 6:
                continue

            values.append(float(text))

        if len(values) >= fund_count:
            nav_values = values[:fund_count]
            break

    if nav_values is None:
        raise ValueError("Arena PDF: NAV row not found")

    # --------------------------------------------------
    # 6. Extract MTD row (first valid one)
    # --------------------------------------------------
    mtd_values = None

    for row in sorted(rows.values(), key=lambda r: r[0]["top"]):
        tokens = build_numeric_tokens(row)
        values = []

        for tok in tokens:
            text = "".join(c["text"] for c in tok).replace("%", "").strip()

            if not text:
                continue
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
    # 7. Build final output
    # --------------------------------------------------
    wf["NAV"] = nav_values
    wf["MTD"] = mtd_values
    wf["Variance"] = abs(wf["MTD"])

    return wf

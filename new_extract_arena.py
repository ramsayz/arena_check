import pdfplumber
import pandas as pd
import re

def extract_arena(file_path, workflow_path):

    # -------------------------------------------------
    # 1. Read workflow (Arena funds only)
    # -------------------------------------------------
    wf = pd.read_excel(workflow_path)
    wf = wf[wf["Fund Name"].str.contains("Arena", case=False, na=False)]
    wf = wf.reset_index(drop=True)

    if wf.empty:
        raise ValueError("Arena: No Arena funds found in workflow")

    # -------------------------------------------------
    # 2. Read PDF characters
    # -------------------------------------------------
    chars = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            chars.extend(page.chars)

    if not chars:
        raise ValueError("Arena PDF: No text extracted")

    # -------------------------------------------------
    # 3. Group characters by Y (rows)
    # -------------------------------------------------
    rows = {}
    for c in chars:
        y = round(c["top"], 1)
        rows.setdefault(y, []).append(c)

    # -------------------------------------------------
    # 4. Identify NAV row and MTD row by content
    # -------------------------------------------------
    nav_row = None
    mtd_row = None

    for y, row in rows.items():
        text = "".join(ch["text"] for ch in row)

        # NAV row: many comma numbers, no %
        if nav_row is None and len(re.findall(r"\d{1,3},\d{3}", text)) >= 5 and "%" not in text:
            nav_row = row

        # MTD row: % values
        if mtd_row is None and "%" in text:
            mtd_row = row

    if nav_row is None or mtd_row is None:
        raise ValueError("Arena PDF: Could not locate NAV or MTD row")

    # -------------------------------------------------
    # 5. Split a row into columns using X gaps
    # -------------------------------------------------
    def split_into_columns(row, gap=25):
        row = sorted(row, key=lambda x: x["x0"])
        cols = []
        current = [row[0]]

        for c in row[1:]:
            if c["x0"] - current[-1]["x1"] <= gap:
                current.append(c)
            else:
                cols.append(current)
                current = [c]

        cols.append(current)

        return [
            "".join(ch["text"] for ch in col).strip()
            for col in cols
        ]

    nav_cols = split_into_columns(nav_row)
    mtd_cols = split_into_columns(mtd_row)

    # -------------------------------------------------
    # 6. Extract NAV values (skip DATE column)
    # -------------------------------------------------
    nav_values = []
    for col in nav_cols:
        c = col.replace(" ", "")

        # skip date column
        if "/" in c:
            continue

        # strict NAV pattern
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+", c):
            nav_values.append(float(c.replace(",", "")))

    # -------------------------------------------------
    # 7. Extract MTD values
    # -------------------------------------------------
    mtd_values = []
    for col in mtd_cols:
        if "%" in col:
            mtd_values.append(float(col.replace("%", "").strip()))

    # -------------------------------------------------
    # 8. HARD VALIDATION (no silent corruption)
    # -------------------------------------------------
    if not nav_values or not mtd_values:
        raise ValueError("Arena PDF: NAV or MTD values empty after extraction")

    if len(nav_values) != len(mtd_values):
        raise ValueError(
            f"Arena PDF mismatch: NAV={len(nav_values)}, MTD={len(mtd_values)}"
        )

    if len(nav_values) != len(wf):
        raise ValueError(
            f"Arena vs Workflow mismatch: Arena={len(nav_values)}, Workflow={len(wf)}"
        )

    # -------------------------------------------------
    # 9. Build final output
    # -------------------------------------------------
    wf["NAV"] = nav_values
    wf["MTD"] = mtd_values
    wf["Variance"] = abs(wf["MTD"])

    return wf

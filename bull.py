import pdfplumber
import pandas as pd
import re
from collections import defaultdict

def extract_arena(file_path, workflow_path):

    # --------------------------------------------------
    # 1. Read workflow (Arena funds only)
    # --------------------------------------------------
    wf = pd.read_excel(workflow_path)
    wf = wf[wf["Fund Name"].str.contains("Arena", case=False, na=False)]
    wf = wf.reset_index(drop=True)

    if wf.empty:
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
    # 3. Group characters by Y-position (rows)
    # --------------------------------------------------
    rows = defaultdict(list)
    for c in chars:
        rows[round(c["top"], 1)].append(c)

    # --------------------------------------------------
    # 4. Identify NAV row and MTD row
    # --------------------------------------------------
    nav_row = None
    mtd_row = None

    for row in rows.values():
        text = "".join(ch["text"] for ch in row)

        # NAV row → many comma numbers, no %
        if nav_row is None and "%" not in text and len(re.findall(r"\d{1,3},\d{3}", text)) >= 5:
            nav_row = row

        # MTD row → contains %
        if mtd_row is None and "%" in text:
            mtd_row = row

    if nav_row is None or mtd_row is None:
        raise ValueError("Arena PDF: NAV or MTD row not found")

    # --------------------------------------------------
    # 5. Cluster characters into columns using x-centers
    # --------------------------------------------------
    def cluster_columns(row, tolerance=8):
        columns = []
        for c in sorted(row, key=lambda x: (x["x0"] + x["x1"]) / 2):
            cx = (c["x0"] + c["x1"]) / 2
            placed = False
            for col in columns:
                if abs(cx - col["cx"]) <= tolerance:
                    col["chars"].append(c)
                    placed = True
                    break
            if not placed:
                columns.append({"cx": cx, "chars": [c]})
        return columns

    nav_cols = cluster_columns(nav_row)
    mtd_cols = cluster_columns(mtd_row)

    # --------------------------------------------------
    # 6. Extract NAV values (STRICT)
    # --------------------------------------------------
    nav_values = []
    for col in nav_cols:
        raw = "".join(c["text"] for c in col["chars"])
        cleaned = raw.replace(",", "").strip()

        # skip dates / fragments / empty
        if not cleaned:
            continue
        if "/" in cleaned:
            continue
        if not cleaned.isdigit():
            continue

        nav_values.append(float(cleaned))

    # --------------------------------------------------
    # 7. Extract MTD values (STRICT)
    # --------------------------------------------------
    mtd_values = []
    for col in mtd_cols:
        raw = "".join(c["text"] for c in col["chars"])
        cleaned = raw.replace("%", "").strip()

        if not cleaned:
            continue
        if "/" in cleaned:
            continue

        try:
            mtd_values.append(float(cleaned))
        except ValueError:
            continue

    # --------------------------------------------------
    # 8. Hard validation (no silent corruption)
    # --------------------------------------------------
    if not nav_values or not mtd_values:
        raise ValueError("Arena PDF: NAV or MTD values empty after extraction")

    if len(nav_values) != len(mtd_values):
        raise ValueError(
            f"Arena mismatch: NAV={len(nav_values)}, MTD={len(mtd_values)}"
        )

    if len(nav_values) != len(wf):
        raise ValueError(
            f"Arena vs Workflow mismatch: Arena={len(nav_values)}, Workflow={len(wf)}"
        )

    # --------------------------------------------------
    # 9. Build final output
    # --------------------------------------------------
    wf["NAV"] = nav_values
    wf["MTD"] = mtd_values
    wf["Variance"] = abs(wf["MTD"])

    return wf

import pdfplumber
import pandas as pd
import re
from collections import defaultdict

def extract_arena(file_path, workflow_path):

    # 1. Read workflow
    wf = pd.read_excel(workflow_path)
    wf = wf[wf["Fund Name"].str.contains("Arena", case=False, na=False)]
    wf = wf.reset_index(drop=True)

    if wf.empty:
        raise ValueError("Arena: No Arena funds in workflow")

    # 2. Read all chars
    chars = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            chars.extend(page.chars)

    if not chars:
        raise ValueError("Arena PDF: No text extracted")

    # 3. Group chars by Y (rows)
    rows = defaultdict(list)
    for c in chars:
        rows[round(c["top"], 1)].append(c)

    # 4. Identify NAV row and MTD row by content
    nav_row = None
    mtd_row = None

    for row in rows.values():
        text = "".join(c["text"] for c in row)

        if nav_row is None and len(re.findall(r"\d{1,3},\d{3}", text)) >= 5 and "%" not in text:
            nav_row = row

        if mtd_row is None and "%" in text:
            mtd_row = row

    if nav_row is None or mtd_row is None:
        raise ValueError("Arena PDF: NAV or MTD row not found")

    # 5. Cluster characters into columns using X-center
    def cluster_columns(row, tol=8):
        cols = []
        for c in sorted(row, key=lambda x: (x["x0"] + x["x1"]) / 2):
            cx = (c["x0"] + c["x1"]) / 2
            placed = False
            for col in cols:
                col_cx = col["cx"]
                if abs(cx - col_cx) <= tol:
                    col["chars"].append(c)
                    placed = True
                    break
            if not placed:
                cols.append({"cx": cx, "chars": [c]})
        return cols

    nav_cols = cluster_columns(nav_row)
    mtd_cols = cluster_columns(mtd_row)

    # 6. Extract NAV values (skip date column)
    nav_values = []
    for col in nav_cols:
        text = "".join(c["text"] for c in col["chars"]).replace(" ", "")
        if "/" in text:
            continue
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+", text):
            nav_values.append(float(text.replace(",", "")))

    # 7. Extract MTD values
    mtd_values = []
    for col in mtd_cols:
        text = "".join(c["text"] for c in col["chars"])
        if "%" in text:
            mtd_values.append(float(text.replace("%", "").strip()))

    # 8. Hard validation
    if not nav_values or not mtd_values:
        raise ValueError("Arena PDF: NAV or MTD values empty after extraction")

    if len(nav_values) != len(mtd_values):
        raise ValueError(f"Arena mismatch: NAV={len(nav_values)}, MTD={len(mtd_values)}")

    if len(nav_values) != len(wf):
        raise ValueError(
            f"Arena vs Workflow mismatch: Arena={len(nav_values)}, Workflow={len(wf)}"
        )

    # 9. Output
    wf["NAV"] = nav_values
    wf["MTD"] = mtd_values
    wf["Variance"] = abs(wf["MTD"])

    return wf

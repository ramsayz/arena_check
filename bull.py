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
    # 3. Group characters by row (Y)
    # --------------------------------------------------
    rows = defaultdict(list)
    for c in chars:
        rows[round(c["top"], 1)].append(c)

    # --------------------------------------------------
    # 4. Column clustering by x-center
    # --------------------------------------------------
    def cluster_columns(row, tol=8):
        cols = []
        for c in sorted(row, key=lambda x: (x["x0"] + x["x1"]) / 2):
            cx = (c["x0"] + c["x1"]) / 2
            placed = False
            for col in cols:
                if abs(cx - col["cx"]) <= tol:
                    col["chars"].append(c)
                    placed = True
                    break
            if not placed:
                cols.append({"cx": cx, "chars": [c]})
        return cols

    # --------------------------------------------------
    # 5. Find NAV row (FIRST valid one only)
    # --------------------------------------------------
    nav_values = None

    for row in sorted(rows.values(), key=lambda r: r[0]["top"]):
        cols = cluster_columns(row)
        vals = []

        for col in cols:
            raw = "".join(c["text"] for c in col["chars"])
            cleaned = raw.replace(",", "").strip()

            if not cleaned:
                continue
            if "/" in cleaned:
                continue
            if not cleaned.isdigit():
                continue

            vals.append(float(cleaned))

        if len(vals) == fund_count:
            nav_values = vals
            break

    if nav_values is None:
        raise ValueError("Arena PDF: NAV row not found")

    # --------------------------------------------------
    # 6. Find MTD row (FIRST valid one only)
    # --------------------------------------------------
    mtd_values = None

    for row in sorted(rows.values(), key=lambda r: r[0]["top"]):
        cols = cluster_columns(row)
        vals = []

        for col in cols:
            raw = "".join(c["text"] for c in col["chars"])
            cleaned = raw.replace("%", "").strip()

            if not cleaned:
                continue
            if "/" in cleaned:
                continue

            try:
                vals.append(float(cleaned))
            except ValueError:
                continue

        if len(vals) == fund_count:
            mtd_values = vals
            break

    if mtd_values is None:
        raise ValueError("Arena PDF: MTD row not found")

    # --------------------------------------------------
    # 7. Build output
    # --------------------------------------------------
    wf["NAV"] = nav_values
    wf["MTD"] = mtd_values
    wf["Variance"] = abs(wf["MTD"])

    return wf

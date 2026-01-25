def extract_arena(file_path, workflow_path):
    import pdfplumber
    import pandas as pd
    import re

    # -------------------------------------------------
    # 1. Read characters from first page
    # -------------------------------------------------
    with pdfplumber.open(file_path) as pdf:
        page = pdf.pages[0]
        chars = page.chars

    if not chars:
        raise ValueError("Arena PDF: no characters extracted")

    # -------------------------------------------------
    # 2. Group characters by Y position (rows)
    # -------------------------------------------------
    rows = {}
    for c in chars:
        y = round(c["top"], 1)
        rows.setdefault(y, []).append(c)

    # -------------------------------------------------
    # 3. Rebuild text per row (purely for token search)
    # -------------------------------------------------
    row_text = {}
    for y, rchars in rows.items():
        text = "".join(
            c["text"] for c in sorted(rchars, key=lambda x: x["x0"])
        )
        row_text[y] = text

    # -------------------------------------------------
    # 4. Numeric-density detection (THE KEY FIX)
    # -------------------------------------------------
    row_metrics = {}

    for y, text in row_text.items():
        nav_nums = re.findall(r'\d{1,3}(?:,\d{3})+', text)
        mtd_nums = re.findall(r'-?\d+\.\d+%', text)

        row_metrics[y] = {
            "nav_count": len(nav_nums),
            "mtd_count": len(mtd_nums),
            "nav_nums": nav_nums,
            "mtd_nums": mtd_nums
        }

    # NAV row = row with MAX comma-number count
    nav_row_y = max(row_metrics, key=lambda y: row_metrics[y]["nav_count"])
    mtd_row_y = max(row_metrics, key=lambda y: row_metrics[y]["mtd_count"])

    nav_tokens = row_metrics[nav_row_y]["nav_nums"]
    mtd_tokens = row_metrics[mtd_row_y]["mtd_nums"]

    if not nav_tokens or not mtd_tokens:
        raise ValueError("Arena PDF: failed to detect NAV or MTD values")

    # -------------------------------------------------
    # 5. Convert values
    # -------------------------------------------------
    nav_values = [float(x.replace(",", "")) for x in nav_tokens]
    mtd_values = [float(x.replace("%", "")) for x in mtd_tokens]

    # -------------------------------------------------
    # 6. Load workflow (SOURCE OF TRUTH)
    # -------------------------------------------------
    wf = pd.read_excel(workflow_path)
    wf = wf[['Fund UCN', 'Fund Name', 'DATE', 'NAV (thous)']]
    wf.rename(columns={'NAV (thous)': 'Prev NAV'}, inplace=True)

    wf['NAV Date'] = nav_date(wf['DATE'].tolist())
    wf['NAV Date'] = wf['NAV Date'].dt.strftime("%m/%d/%Y")

    # -------------------------------------------------
    # 7. HARD SAFETY CHECK (prevents silent corruption)
    # -------------------------------------------------
    if len(nav_values) != len(wf):
        raise ValueError(
            f"Arena NAV count ({len(nav_values)}) "
            f"does not match workflow rows ({len(wf)})"
        )

    if len(mtd_values) != len(wf):
        raise ValueError(
            f"Arena MTD count ({len(mtd_values)}) "
            f"does not match workflow rows ({len(wf)})"
        )

    # -------------------------------------------------
    # 8. Index-based assignment (ONLY CORRECT WAY)
    # -------------------------------------------------
    wf['NAV'] = nav_values
    wf['MTD'] = mtd_values

    wf['Prev NAV'] = wf['Prev NAV'].astype(float)
    wf['Variance'] = abs(
        (wf['NAV'] - wf['Prev NAV']) / wf['Prev NAV'] * 100
    )

    wf = wf[
        ['Fund UCN', 'Fund Name', 'NAV Date', 'NAV', 'MTD', 'Prev NAV', 'Variance']
    ].sort_values(by='Variance')

    return wf

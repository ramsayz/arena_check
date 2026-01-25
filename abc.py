def extract_arena(file_path, workflow_path):
    import pdfplumber
    import pandas as pd
    import re

    # --------------------------------------------------
    # 1. Read characters from first page
    # --------------------------------------------------
    with pdfplumber.open(file_path) as pdf:
        page = pdf.pages[0]
        chars = page.chars

    if not chars:
        raise ValueError("Arena PDF: no characters extracted")

    # --------------------------------------------------
    # 2. Group characters by Y position (rows)
    # --------------------------------------------------
    rows = {}
    for c in chars:
        y = round(c["top"], 1)
        rows.setdefault(y, []).append(c)

    # --------------------------------------------------
    # 3. Rebuild raw text per row (x-sorted)
    # --------------------------------------------------
    row_text = {}
    for y, rchars in rows.items():
        text = "".join(
            c["text"] for c in sorted(rchars, key=lambda x: x["x0"])
        )
        row_text[y] = text

    # --------------------------------------------------
    # 4. Detect NAV / MTD rows by NUMERIC DENSITY
    #    (not by text heuristics)
    # --------------------------------------------------
    row_metrics = {}

    for y, text in row_text.items():
        # Capture kerning-split NAV numbers safely
        raw_nav_tokens = re.findall(r'[\d,\s]{7,}', text)
        nav_nums = []
        for tok in raw_nav_tokens:
            cleaned = tok.replace(" ", "")
            if re.fullmatch(r'\d{1,3}(?:,\d{3})+', cleaned):
                nav_nums.append(cleaned)

        # MTD values are safe as-is
        mtd_nums = re.findall(r'-?\d+\.\d+%', text)

        row_metrics[y] = {
            "nav_count": len(nav_nums),
            "mtd_count": len(mtd_nums),
            "nav_nums": nav_nums,
            "mtd_nums": mtd_nums
        }

    # Pick densest numeric rows
    nav_row_y = max(row_metrics, key=lambda y: row_metrics[y]["nav_count"])
    mtd_row_y = max(row_metrics, key=lambda y: row_metrics[y]["mtd_count"])

    nav_tokens = row_metrics[nav_row_y]["nav_nums"]
    mtd_tokens = row_metrics[mtd_row_y]["mtd_nums"]

    if not nav_tokens or not mtd_tokens:
        raise ValueError("Arena PDF: failed to detect NAV or MTD values")

    # --------------------------------------------------
    # 5. Convert values to numeric
    # --------------------------------------------------
    nav_values = [float(x.replace(",", "")) for x in nav_tokens]
    mtd_values = [float(x.replace("%", "")) for x in mtd_tokens]

    # --------------------------------------------------
    # 6. Load workflow (SOURCE OF TRUTH)
    # --------------------------------------------------
    wf = pd.read_excel(workflow_path)
    wf = wf[['Fund UCN', 'Fund Name', 'DATE', 'NAV (thous)']]
    wf.rename(columns={'NAV (thous)': 'Prev NAV'}, inplace=True)

    wf['NAV Date'] = nav_date(wf['DATE'].tolist())
    wf['NAV Date'] = wf['NAV Date'].dt.strftime("%m/%d/%Y")

    # --------------------------------------------------
    # 7. Hard safety checks (prevents silent corruption)
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 8. Index-based assignment (ONLY reliable mapping)
    # --------------------------------------------------
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

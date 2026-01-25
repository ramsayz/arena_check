def extract_arena(file_path, workflow_path):
    import pdfplumber
    import pandas as pd
    import re

    # --------------------------------------------------
    # Helper: split a row into columns using X gaps
    # --------------------------------------------------
    def extract_columns_from_row(row_chars, gap=25):
        row_chars = sorted(row_chars, key=lambda x: x["x0"])
        columns = []
        current = [row_chars[0]]

        for c in row_chars[1:]:
            if c["x0"] - current[-1]["x1"] <= gap:
                current.append(c)
            else:
                columns.append(current)
                current = [c]

        columns.append(current)

        return [
            "".join(ch["text"] for ch in col).strip()
            for col in columns
        ]

    # --------------------------------------------------
    # 1. Read characters (first page only)
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
    # 3. Identify NAV and MTD rows by numeric density
    # --------------------------------------------------
    nav_row_y = None
    mtd_row_y = None
    max_nav_count = 0
    max_mtd_count = 0

    for y, rchars in rows.items():
        cols = extract_columns_from_row(rchars)

        nav_count = sum(1 for c in cols if "," in c and re.search(r"\d", c))
        mtd_count = sum(1 for c in cols if "%" in c)

        if nav_count > max_nav_count:
            max_nav_count = nav_count
            nav_row_y = y

        if mtd_count > max_mtd_count:
            max_mtd_count = mtd_count
            mtd_row_y = y

    if nav_row_y is None or mtd_row_y is None:
        raise ValueError("Arena PDF: failed to locate NAV or MTD rows")

    # --------------------------------------------------
    # 4. Extract NAV values (COLUMN-AWARE)
    # --------------------------------------------------
    nav_cols = extract_columns_from_row(rows[nav_row_y])

    nav_values = []
    for col in nav_cols:
        cleaned = col.replace(" ", "")
        if re.search(r"\d,\d{3}", cleaned):
            nav_values.append(float(cleaned.replace(",", "")))

    # --------------------------------------------------
    # 5. Extract MTD values (COLUMN-AWARE)
    # --------------------------------------------------
    mtd_cols = extract_columns_from_row(rows[mtd_row_y])

    mtd_values = []
    for col in mtd_cols:
        if "%" in col:
            mtd_values.append(float(col.replace("%", "").replace(" ", "")))

    if not nav_values or not mtd_values:
        raise ValueError("Arena PDF: NAV or MTD values empty after extraction")

    # --------------------------------------------------
    # 6. Load workflow (SOURCE OF TRUTH)
    # --------------------------------------------------
    wf = pd.read_excel(workflow_path)
    wf = wf[['Fund UCN', 'Fund Name', 'DATE', 'NAV (thous)']]
    wf.rename(columns={'NAV (thous)': 'Prev NAV'}, inplace=True)

    wf['NAV Date'] = nav_date(wf['DATE'].tolist())
    wf['NAV Date'] = wf['NAV Date'].dt.strftime("%m/%d/%Y")

    # --------------------------------------------------
    # 7. Hard safety checks
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

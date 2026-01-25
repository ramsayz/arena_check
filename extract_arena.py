def extract_arena(file_path, workflow_path):
    import pdfplumber
    import pandas as pd

    # -----------------------------
    # 1. Extract characters
    # -----------------------------
    with pdfplumber.open(file_path) as pdf:
        page = pdf.pages[0]
        chars = page.chars

    # -----------------------------
    # 2. Group chars by Y (rows)
    # -----------------------------
    rows = {}
    for c in chars:
        y = round(c["top"], 1)
        rows.setdefault(y, []).append(c)

    # -----------------------------
    # 3. Rebuild row text
    # -----------------------------
    row_text = {}
    for y, rchars in rows.items():
        text = "".join(
            c["text"] for c in sorted(rchars, key=lambda x: x["x0"])
        )
        row_text[y] = text.strip()

    # -----------------------------
    # 4. Identify NAV and MTD rows
    # -----------------------------
    nav_row = None
    mtd_row = None

    for y, text in row_text.items():
        if "," in text and "%" not in text:
            nav_row = text
        elif "%" in text:
            mtd_row = text

    if nav_row is None or mtd_row is None:
        raise ValueError("Could not locate NAV or MTD row in Arena PDF")

    # -----------------------------
    # 5. Extract numeric values
    # -----------------------------
    nav_values = [
        float(x.replace(",", ""))
        for x in nav_row.split()
        if "," in x
    ]

    mtd_values = [
        float(x.replace("%", ""))
        for x in mtd_row.split()
        if "%" in x
    ]

    # -----------------------------
    # 6. Load workflow
    # -----------------------------
    wf = pd.read_excel(workflow_path)
    wf = wf[['Fund UCN', 'Fund Name', 'DATE', 'NAV (thous)']]
    wf.rename(columns={'NAV (thous)': 'Prev NAV'}, inplace=True)

    wf['NAV Date'] = nav_date(wf['DATE'].tolist())
    wf['NAV Date'] = wf['NAV Date'].dt.strftime("%m/%d/%Y")

    # -----------------------------
    # 7. Safety check
    # -----------------------------
    if len(nav_values) != len(wf):
        raise ValueError(
            f"Arena NAV count ({len(nav_values)}) "
            f"does not match workflow rows ({len(wf)})"
        )

    # -----------------------------
    # 8. Assign by index (KEY FIX)
    # -----------------------------
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

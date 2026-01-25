nav_values = []
for col in nav_cols:
    cleaned = col.replace(" ", "")

    # Skip date column
    if "/" in cleaned:
        continue

    # Must look like a real NAV (with thousands separators)
    if re.fullmatch(r'\d{1,3}(?:,\d{3})+', cleaned):
        nav_values.append(float(cleaned.replace(",", "")))

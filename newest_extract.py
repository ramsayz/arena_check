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
    # 2. Read all PDF characters
    # --------------------------------------------------
    chars = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            chars.extend(page.chars)

    if not chars:
        raise ValueError("Arena PDF: No text extracted")

    # --------------------------------------------------
    # 3. Group characters into rows (by Y position)
    # --------------------------------------------------
    rows = defaultdict(list)
    for c in chars:
        rows[round(c["top"], 1)].append(c)

    # --------------------------------------------------
    # 4. Helper: merge chars into tokens (digits, commas, %)
    # --------------------------------------------------
    def build_tokens(row):
        row = sorted(row, key=lambda x: x["x0"])
        tokens = []
        current = [row[0]]

        for c in row[1:]:
            prev = current[-1]
            if (
                (prev["text"].isdigit() or prev["text"] in ",%")
                and (c["text"].isdigit() or c["text"] in ",%")
            ):
                current.append(c)
            else:
                tokens.append(current)
                current = [c]

        tokens.append(current)
        return tokens

    # --------------------------------------------------
    # 5. Find FUND NAME row (anchor columns)
    # --------------------------------------------------
    fund_row = None
    for row in rows.values():
        text = " ".join(c["text"] for c in row)
        if text.count("Arena") >= fund_count:
            fund_row = row
            break

    if fund_row is None:
        raise ValueError("Arena PDF: Fund name row not found")

    # Column centers from fund names
    fund_tokens = build_tokens(fund_row)
    fund_centers = []

    for tok in fund_tokens:
        xs = [(c["x0"] + c["x1"]) / 2 for c in tok]
        fund_centers.append(sum(xs) / len(xs))

    fund_centers = fund_centers[:fund_count]

    # --------------------------------------------------
    # 6. Find NAV row
    # --------------------------------------------------
    nav_row = None
    for row in rows.values():
        text = "".join(c["text"] for c in row)
        if "," in text and "%" not in text:
            nav_row = row
            break

    if nav_row is None:
        raise ValueError("Arena PDF: NAV row not found")

    # --------------------------------------------------
    # 7. Find MTD row
    # --------------------------------------------------
    mtd_row = None
    for row in rows.values():
        text = "".join(c["text"] for c in row)
        if "%" in text:
            mtd_row = row
            break

    if mtd_row is None:
        raise ValueError("Arena PDF: MTD row not found")

    # --------------------------------------------------
    # 8. Assign tokens to nearest fund column
    # --------------------------------------------------
    def assign_to_columns(tokens, centers, is_nav=True):
        values = [None] * len(centers)

        for tok in tokens:
            raw = "".join(c["text"] for c in tok).strip()
            cleaned = raw.replace(",", "").replace("%", "")

            # Skip dates and junk
            if "/" in cleaned or not cleaned:
                continue

            # NAV must be large numbers (exclude 10, 1, 2025, etc.)
            if is_nav and (not cleaned.isdigit() or len(cleaned) < 6):
                continue

            try:
                val = float(cleaned)
            except ValueError:
                continue

            cx = sum((c["x0"] + c["x1"]) / 2 for c in tok) / len(tok)
            idx = min(range(len(centers)), key=lambda i: abs(cx - centers[i]))
            values[idx] = val

        return values

    nav_tokens = build_tokens(nav_row)
    mtd_tokens = build_tokens(mtd_row)

    nav_values = assign_to_columns(nav_tokens, fund_centers, is_nav=True)
    mtd_values = assign_to_columns(mtd_tokens, fund_centers, is_nav=False)

    # --------------------------------------------------
    # 9. Final validation
    # --------------------------------------------------
    if any(v is None for v in nav_values):
        raise ValueError("Arena PDF: NAV values incomplete after alignment")

    if any(v is None for v in mtd_values):
        raise ValueError("Arena PDF: MTD values incomplete after alignment")

    # --------------------------------------------------
    # 10. Build output
    # --------------------------------------------------
    wf["NAV"] = nav_values
    wf["MTD"] = mtd_values
    wf["Variance"] = abs(wf["MTD"])

    return wf

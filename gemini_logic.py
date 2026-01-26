import pdfplumber
import pandas as pd

def extract_arena_financials(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()

    # 1. Group words by their vertical (top) position to identify rows
    # We will identify the specific rows for AUM and Net Returns by their dates
    aum_row_y = None
    returns_row_y = None
    
    for word in words:
        if "10/1/2025" in word['text']:
            aum_row_y = word['top']
        if "9/30/2025" in word['text']:
            returns_row_y = word['top']

    if not aum_row_y or not returns_row_y:
        return "Could not locate date rows in PDF."

    # 2. Separate words into Headers, AUM values, and MTD values
    headers = [w for w in words if w['top'] < aum_row_y and w['top'] > 50] # Adjust 50 based on logo height
    aum_values = [w for w in words if abs(w['top'] - aum_row_y) < 5]
    mtd_values = [w for w in words if abs(w['top'] - returns_row_y) < 5]

    # 3. Logic to merge multi-line headers based on X-coordinate (horizontal position)
    fund_data = {}

    for val in aum_values:
        if "/" in val['text']: continue # Skip the date itself
        
        # Find header words that align horizontally with this value
        # We allow a small margin (tolerance) for alignment
        name_parts = [h['text'] for h in headers if abs(h['x0'] - val['x0']) < 40 or abs(h['x1'] - val['x1']) < 40]
        full_name = " ".join(name_parts).strip()
        
        # Match with MTD return by finding the value at the same X-coordinate in the returns row
        mtd_match = next((m['text'] for m in mtd_values if abs(m['x0'] - val['x0']) < 20), "N/A")
        
        fund_data[full_name] = {
            "NAV_AUM": val['text'],
            "MTD_Return": mtd_match
        }

    # 4. Convert to Clean DataFrame
    final_df = pd.DataFrame.from_dict(fund_data, orient='index').reset_index()
    final_df.columns = ['Fund Name', 'AUM (10/1/2025)', 'MTD Return (9/30/2025)']
    
    return final_df

# --- Execution ---
# df = extract_arena_financials("arena_report.pdf")
# print(df.to_string())
# df.to_csv("arena_extracted_data.csv", index=False)

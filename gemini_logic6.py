import pdfplumber
import pandas as pd
import re

def clean_noise(text):
    """Universal cleaner for watermark artifacts and headers."""
    # Removes single lowercase characters (e.g., 'a', 'o', 'c', 'n')
    text = re.sub(r'\b[a-z]\b', '', text)
    # Removes specific structural text that often bleeds into the extraction
    text = re.sub(r'\b(Beginning|of|Month|AUM|Net|Returns|Arena)\b', '', text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip()

def extract_adaptive_arena(pdf_path):
    all_rows = []
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        
        # 1. DYNAMIC ANCHORING: Find row Y-coordinates by searching for dates
        # This handles PDFs where the table might be higher or lower on the page
        aum_row_y = next((w['top'] for w in words if re.search(r'\d{1,2}/\d{1,2}/\d{4}', w['text']) and w['top'] < 400), None)
        returns_row_y = next((w['top'] for w in words if re.search(r'\d{1,2}/\d{1,2}/\d{4}', w['text']) and w['top'] > 400), None)

        def get_row_values(target_y):
            """Groups fragments into unified numbers based on proximity, not fixed positions."""
            row_items = [w for w in words if abs(w['top'] - target_y) < 15 and not re.search(r'\d{1,2}/', w['text'])]
            row_items.sort(key=lambda x: x['x0'])
            
            merged = []
            if not row_items: return merged
            
            curr = row_items[0]
            for next_w in row_items[1:]:
                # If the gap is small (< 5 pixels), it's the same number/value
                if (next_w['x0'] - curr['x1']) < 5:
                    curr['text'] += next_w['text']
                    curr['x1'] = next_w['x1']
                else:
                    merged.append(curr)
                    curr = next_w
            merged.append(curr)
            return merged

        # 2. Extract values using the dynamic anchors
        aum_list = get_row_values(aum_row_y)
        mtd_list = get_row_values(returns_row_y)

        # 3. MAPPING: Match Fund Names to AUM to MTD
        for aum in aum_list:
            # Look up vertically from the AUM value to collect the name
            # We use the AUM's horizontal 'center' to find its column
            mid_x = (aum['x0'] + aum['x1']) / 2
            
            header_parts = [
                w for w in words 
                if w['x0'] < mid_x + 20 and w['x1'] > mid_x - 20 # Column alignment
                and w['top'] < aum_row_y - 10                    # Above the AUM row
                and w['top'] > aum_row_y - 150                   # Within reasonable header height
            ]
            header_parts.sort(key=lambda x: (x['top'], x['x0']))
            
            fund_name = clean_noise(" ".join([h['text'] for h in header_parts]))
            
            # Match the MTD return in the same vertical column
            mtd_match = next((m['text'] for m in mtd_list if abs(((m['x0']+m['x1'])/2) - mid_x) < 30), "N/A")
            
            # Clean the MTD (remove the 'a' artifact)
            mtd_final = re.sub(r'[^0-9.\-%]', '', mtd_match) if mtd_match != "N/A" else "N/A"

            if len(fund_name) > 2:
                all_rows.append({
                    "Fund Name": fund_name,
                    "AUM Value": aum['text'],
                    "MTD Return": mtd_final if mtd_final else "N/A"
                })

    return pd.DataFrame(all_rows)

# Run
# df = extract_adaptive_arena("new_report_file.pdf")
# print(df)

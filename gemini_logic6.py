import pdfplumber
import pandas as pd
import re

def clean_strict(text, is_mtd=False):
    """Aggressively removes watermark noise and non-financial characters."""
    if is_mtd:
        # Keep only numbers, dots, and signs for MTD
        cleaned = re.sub(r'[^0-9.\-%]', '', text)
        return cleaned if cleaned else "N/A"
    
    # Remove single lowercase letters (watermark 'a', 'o', 'c', etc.)
    text = re.sub(r'\b[a-z]\b', '', text)
    # Remove table metadata that sits above the funds
    text = re.sub(r'\b(Beginning|Month|AUM|Net|Returns|Fund|Value)\b', '', text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip()

def extract_arena_surgical(pdf_path):
    all_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        
        # 1. Dynamically find the data rows by looking for date patterns
        # Row 1: AUM (e.g., 10/1/2025) | Row 2: Returns (e.g., 9/30/2025)
        aum_row = next((w for w in words if re.search(r'\d{1,2}/\d{1,2}/202', w['text']) and w['top'] < 400), None)
        mtd_row = next((w for w in words if re.search(r'\d{1,2}/\d{1,2}/202', w['text']) and w['top'] > 400), None)

        if not aum_row or not mtd_row:
            return "Required date rows not found."

        # 2. Get numbers from the rows, merging fragments (like '9' and '5,000,000')
        def get_merged_line_values(target_y):
            line_words = [w for w in words if abs(w['top'] - target_y) < 10 and "/" not in w['text']]
            line_words.sort(key=lambda x: x['x0'])
            
            merged = []
            if not line_words: return merged
            curr = line_words[0]
            for nxt in line_words[1:]:
                if (nxt['x0'] - curr['x1']) < 4: # Very tight gap = same number
                    curr['text'] += nxt['text']
                    curr['x1'] = nxt['x1']
                else:
                    merged.append(curr)
                    curr = nxt
            merged.append(curr)
            return merged

        aums = get_merged_line_values(aum_row['top'])
        mtds = get_merged_line_values(mtd_row['top'])

        # 3. Use the horizontal center of each AUM as the search column
        for aum in aums:
            center_x = (aum['x0'] + aum['x1']) / 2
            
            # SUCK UP: Only take text directly above this number's center
            header_parts = [
                w for w in words 
                if w['x0'] < center_x + 25 and w['x1'] > center_x - 25 # Strict column slice
                and w['top'] < aum_row['top'] - 5                     # Above AUM row
                and w['top'] > aum_row['top'] - 120                   # Below top logo
            ]
            header_parts.sort(key=lambda x: (x['top'], x['x0']))
            
            # Match MTD return in the same vertical slice
            mtd_raw = next((m['text'] for m in mtds if abs(((m['x0']+m['x1'])/2) - center_x) < 30), "N/A")
            
            fund_name = clean_strict(" ".join([h['text'] for h in header_parts]))
            
            if len(fund_name) > 3:
                all_data.append({
                    "Fund Name": fund_name,
                    "AUM (NAV)": aum['text'],
                    "MTD Return": clean_strict(mtd_raw, is_mtd=True)
                })

    return pd.DataFrame(all_data)

# Execution
# df = extract_arena_surgical("arena_report.pdf")
# print(df.to_string())

import pdfplumber
import pandas as pd
import re

def extract_and_clean_arena(pdf_path):
    all_data = []
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        
        # 1. Locate row anchors (Dates)
        aum_row = next((w for w in words if re.search(r'\d{1,2}/\d{1,2}/202', w['text']) and w['top'] < 400), None)
        mtd_row = next((w for w in words if re.search(r'\d{1,2}/\d{1,2}/202', w['text']) and w['top'] > 400), None)

        def get_merged_values(target_y):
            line = [w for w in words if abs(w['top'] - target_y) < 12 and "/" not in w['text']]
            line.sort(key=lambda x: x['x0'])
            merged = []
            if not line: return merged
            curr = line[0]
            for nxt in line[1:]:
                if (nxt['x0'] - curr['x1']) < 5:
                    curr['text'] += nxt['text']
                    curr['x1'] = nxt['x1']
                else:
                    merged.append(curr)
                    curr = nxt
            merged.append(curr)
            return merged

        aums = get_merged_values(aum_row['top'])
        mtds = get_merged_values(mtd_row['top'])

        for aum in aums:
            mid_x = (aum['x0'] + aum['x1']) / 2
            # Extract Fund Name (Vertical Straw Logic)
            header_parts = [w for w in words if abs(((w['x0']+w['x1'])/2) - mid_x) < 30 
                            and w['top'] < aum_row['top'] - 5 and w['top'] > aum_row['top'] - 130]
            header_parts.sort(key=lambda x: (x['top'], x['x0']))
            raw_name = " ".join([h['text'] for h in header_parts])
            
            # Match MTD Return
            mtd_raw = next((m['text'] for m in mtds if abs(((m['x0']+m['x1'])/2) - mid_x) < 30), "0")
            
            # CLEANING STEP: Remove commas and alphabets
            clean_aum = re.sub(r'[^0-9.\-]', '', aum['text'])
            clean_mtd = re.sub(r'[^0-9.\-]', '', mtd_raw)
            clean_name = re.sub(r'\b[a-z]\b|\b(Beginning|Month|AUM|Net|Returns|Fund|Value)\b', '', raw_name, flags=re.IGNORECASE).strip()

            if len(clean_name) > 3:
                all_data.append({
                    "Fund Name": clean_name,
                    "AUM": clean_aum,
                    "MTD": clean_mtd
                })

    df = pd.DataFrame(all_data)
    
    # FINAL NUMERICAL CONVERSION
    df['AUM'] = pd.to_numeric(df['AUM'], errors='coerce').fillna(0)
    df['MTD'] = pd.to_numeric(df['MTD'], errors='coerce').fillna(0)
    
    return df

# df = extract_and_clean_arena("your_file.pdf")

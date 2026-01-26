import pdfplumber
import pandas as pd
import re

def clean_fund_name(name):
    """Removes stray letters, watermark artifacts, and structural headers."""
    # Remove structural table headers that bleed into the name
    name = re.sub(r'\b(Beginning|of|Month|AUM|Net|Returns)\b', '', name, flags=re.IGNORECASE)
    # Remove specific watermark/noise patterns like 'o c n', 'a g r', etc.
    name = re.sub(r'\b[a-z]\b', '', name) 
    # Remove any extra dots or stray characters left over
    name = re.sub(r'[^a-zA-Z0-9\s(),.\-]', '', name)
    return " ".join(name.split()).strip()

def extract_arena_final(pdf_path):
    all_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        
        # 1. Locate anchors for the rows
        aum_row_y = next((w['top'] for w in words if "10/1/2025" in w['text']), None)
        returns_row_y = next((w['top'] for w in words if "9/30/2025" in w['text']), None)

        # 2. Extract and MERGE split numbers (Fixes the "9" and "5,000,000" issue)
        def get_merged_values(y_coord):
            row_words = [w for w in words if abs(w['top'] - y_coord) < 3 and "/" not in w['text']]
            row_words.sort(key=lambda x: x['x0'])
            
            merged = []
            if not row_words: return merged
            
            current = row_words[0]
            for next_w in row_words[1:]:
                # If words are very close horizontally, merge them
                if next_w['x0'] - current['x1'] < 5: 
                    current['text'] += next_w['text']
                    current['x1'] = next_w['x1']
                else:
                    merged.append(current)
                    current = next_w
            merged.append(current)
            return merged

        aum_vals = get_merged_values(aum_row_y)
        mtd_vals = get_merged_values(returns_row_y)

        # 3. Associate names with values
        for aum in aum_vals:
            # Look UP for the header
            header_parts = [
                w for w in words 
                if abs(w['x0'] - aum['x0']) < 50 
                and w['top'] < aum_row_y 
                and w['top'] > (aum_row_y - 100)
            ]
            header_parts.sort(key=lambda x: (x['top'], x['x0']))
            
            raw_name = " ".join([h['text'] for h in header_parts])
            fund_name = clean_fund_name(raw_name)
            
            # Match MTD return by X coordinate
            mtd_match = next((m['text'] for m in mtd_vals if abs(m['x0'] - aum['x0']) < 20), "N/A")
            
            # Only add if we have a valid-looking fund name
            if len(fund_name) > 5:
                all_data.append({
                    "Fund Name": fund_name,
                    "AUM (10/1/2025)": aum['text'],
                    "MTD Return (9/30/2025)": mtd_match
                })

    return pd.DataFrame(all_data)

# df = extract_arena_final("your_file.pdf")
# print(df.to_string())

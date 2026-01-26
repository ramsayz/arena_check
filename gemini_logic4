import pdfplumber
import pandas as pd
import re

def clean_text(text):
    """Aggressive cleaning of watermark noise and structural headers."""
    # Remove single lowercase letters (watermark artifacts like 'o c n')
    text = re.sub(r'\b[a-z]\b', '', text)
    # Remove structural table headers
    text = re.sub(r'\b(Beginning|of|Month|AUM|Net|Returns)\b', '', text, flags=re.IGNORECASE)
    # Clean up whitespace
    return " ".join(text.split()).strip()

def extract_arena_fixed_final(pdf_path):
    all_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        
        # 1. Identify row Y-coordinates
        aum_row_y = next((w['top'] for w in words if "10/1/2025" in w['text']), None)
        returns_row_y = next((w['top'] for w in words if "9/30/2025" in w['text']), None)

        def get_unified_values(target_y, threshold=12):
            """
            Captures words within a vertical threshold to handle split numbers 
            (e.g., catching '9' and '5,000,000' even if they are slightly misaligned).
            """
            row_words = [w for w in words if abs(w['top'] - target_y) < threshold and "/" not in w['text']]
            row_words.sort(key=lambda x: x['x0'])
            
            unified = []
            if not row_words: return unified
            
            curr = row_words[0]
            for next_w in row_words[1:]:
                # If words are extremely close horizontally, they are part of the same number
                if (next_w['x0'] - curr['x1']) < 4:
                    curr['text'] += next_w['text']
                    curr['x1'] = next_w['x1']
                else:
                    unified.append(curr)
                    curr = next_w
            unified.append(curr)
            return unified

        # 2. Get the merged AUM and MTD value lists
        aum_vals = get_unified_values(aum_row_y)
        mtd_vals = get_unified_values(returns_row_y)

        # 3. Build the dataset
        for aum in aum_vals:
            # Find the Fund Name by looking directly above the AUM value
            header_parts = [
                w for w in words 
                if abs(w['x0'] - aum['x0']) < 45  # Column width tolerance
                and w['top'] < aum_row_y 
                and w['top'] > (aum_row_y - 110)
            ]
            header_parts.sort(key=lambda x: (x['top'], x['x0']))
            
            fund_name = clean_text(" ".join([h['text'] for h in header_parts]))
            
            # Match the MTD Return using the same X-coordinate (horizontal position)
            # Use a slightly wider tolerance (30) to ensure we catch the % sign
            mtd_match = next((m['text'] for m in mtd_vals if abs(m['x0'] - aum['x0']) < 30), "N/A")
            
            if len(fund_name) > 5:
                all_data.append({
                    "Fund Name": fund_name,
                    "AUM (10/1/2025)": aum['text'],
                    "MTD Return (9/30/2025)": mtd_match
                })

    return pd.DataFrame(all_data)

# Usage:
# df = extract_arena_fixed_final("arena_investors.pdf")
# print(df.to_string())

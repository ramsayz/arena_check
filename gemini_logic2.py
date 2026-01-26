
def clean_fund_name(name):
    """Removes stray letters and watermark artifacts."""
    # Remove common artifacts like 'Beginning of Month' or stray single letters
    name = re.sub(r'\b(Beginning|of|Month|AUM|Net|Returns)\b', '', name, flags=re.IGNORECASE)
    # Remove single letters that aren't 'I', 'V', or 'A' (common in finance)
    name = re.sub(r'\b(?![IVAiv]\b)[a-zA-Z]\b', '', name)
    return " ".join(name.split()).strip()

def extract_arena_data_pro(pdf_path):
    all_data = []
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        
        # 1. Locate the horizontal 'Y' level for AUM and Returns
        aum_row_y = None
        returns_row_y = None
        
        for w in words:
            if "10/1/2025" in w['text']: aum_row_y = w['top']
            if "9/30/2025" in w['text']: returns_row_y = w['top']

        if not aum_row_y or not returns_row_y:
            return "Error: Could not find date rows."

        # 2. Extract the actual numbers (AUM and MTD)
        # We target words on the same line as the dates, excluding the dates themselves
        aum_vals = [w for w in words if abs(w['top'] - aum_row_y) < 3 and "/" not in w['text']]
        mtd_vals = [w for w in words if abs(w['top'] - returns_row_y) < 3 and "/" not in w['text']]

        # 3. For each AUM value, look directly UP to find the header text
        for aum in aum_vals:
            # Get words that are vertically aligned with this AUM value (X-axis)
            # but sit above the AUM row (Y-axis)
            header_words = [
                w for w in words 
                if abs(w['x0'] - aum['x0']) < 40  # Horizontal alignment tolerance
                and w['top'] < aum_row_y          # Must be above the AUM row
                and w['top'] > (aum_row_y - 120)  # Limit height to avoid top logo
            ]
            
            # Sort words by top-to-bottom and left-to-right to reconstruct the name
            header_words.sort(key=lambda x: (x['top'], x['x0']))
            raw_name = " ".join([h['text'] for h in header_words])
            fund_name = clean_fund_name(raw_name)
            
            # Find the corresponding MTD return on the returns row at the same X-position
            mtd_match = next((m['text'] for m in mtd_vals if abs(m['x0'] - aum['x0']) < 20), "N/A")
            
            all_data.append({
                "Fund Name": fund_name,
                "AUM (10/1/2025)": aum['text'],
                "MTD Return (9/30/2025)": mtd_match
            })

    # 4. Final Cleanup and DataFrame
    df = pd.DataFrame(all_data)
    # Filter out empty or garbage rows if any
    df = df[df['Fund Name'].str.len() > 3].reset_index(drop=True)
    return df

# Run the script
# df = extract_arena_data_pro("your_file.pdf")
# print(df.to_string())

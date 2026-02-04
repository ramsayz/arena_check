def parse_fund_name(x):
    if pd.isna(x):
        return pd.Series([None, None, None, None, None])

    x = x.upper().strip()

    # Base name: everything before '(' or ','
    base = re.split(r'\(|,', x)[0].strip()

    entity = (
        'PARTNERS' if 'PARTNERS' in x else
        'MASTER' if 'MASTER' in x else
        None
    )

    jurisdiction = (
        'CAYMAN' if 'CAYMAN' in x else
        'OFFSHORE' if 'OFFSHORE' in x else
        None
    )

    roman = re.search(r'\b(I{1,3}|IV|V)\b', x)
    roman = roman.group(0) if roman else None

    legal = (
        'LP' if re.search(r'\bLP\b', x) else
        'LLC' if 'LLC' in x else
        None
    )

    return pd.Series([base, entity, jurisdiction, roman, legal])

proxy_df = wf[['Proxy']].drop_duplicates().copy()

proxy_df[['base','entity','jurisdiction','roman','legal']] = (
    proxy_df['Proxy'].apply(parse_fund_name)
)
pre_df[['base','entity','jurisdiction','roman','legal']] = (
    pre_df['Fund Name'].apply(parse_fund_name)
)
base_choices = proxy_df['base'].dropna().unique().tolist()

def fuzzy_base_match(x):
    if not x:
        return None

    match, score = process.extractOne(
        x,
        base_choices,
        scorer=fuzz.token_set_ratio
    )

    return match if score >= 92 else None
pre_df['base_match'] = pre_df['base'].apply(fuzzy_base_match)
def resolve_proxy(row):
    if row['base_match'] is None:
        return None

    candidates = proxy_df[
        (proxy_df['base'] == row['base_match']) &
        (proxy_df['entity'] == row['entity']) &
        (proxy_df['jurisdiction'] == row['jurisdiction']) &
        (proxy_df['roman'] == row['roman']) &
        (proxy_df['legal'] == row['legal'])
    ]

    if len(candidates) == 1:
        return candidates.iloc[0]['Proxy']

    return None  # ambiguous or no match
pre_df['Matched_Proxy'] = pre_df.apply(resolve_proxy, axis=1)
# Unmatched or ambiguous rows
audit_df = pre_df[pre_df['Matched_Proxy'].isna()][
    ['Fund Name','base','entity','jurisdiction','roman','legal']
]

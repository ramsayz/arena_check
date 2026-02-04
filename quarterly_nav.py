month = prev_nav_date_format.month
    current_quarter = ((month - 1) // 3) + 1

    # Step 5: next quarter end month
    next_quarter = current_quarter + 1
    if next_quarter > 4:
        next_quarter = 1
        year = prev_nav_date_format.year + 1
    else:
        year = prev_nav_date_format.year

    quarter_end_month = next_quarter * 3

    # Step 6: compute quarter-end date
    next_quarter_end_date = (
        datetime(year, quarter_end_month, 1)
        + relativedelta(months=1, days=-1)
    )

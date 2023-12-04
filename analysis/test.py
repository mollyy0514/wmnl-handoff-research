for target_event in ho_types:
    # target_event = 'SCGA'
    # print(target_event)

    # Use .loc to explicitly create a copy of the selected rows
    selected_rows = rate_table2.loc[
        (rate_table2.index.get_level_values(0) == target_event) | (rate_table2.index.get_level_values(1) == target_event)
    ].copy()

    for (idx_x, idx_y), row in selected_rows.iterrows():
        if idx_x != target_event:
            # Use .loc to modify the copy
            selected_rows.loc[(idx_y, idx_x), :] = row.copy()
            for mets in ['lost', 'excl', 'loex']:
                selected_rows.at[(idx_y, idx_x), f'{mets}_x_r (%)'] = row[f'{mets}_y_r (%)']
                selected_rows.at[(idx_y, idx_x), f'{mets}_y_r (%)'] = row[f'{mets}_x_r (%)']
                selected_rows.at[(idx_y, idx_x), f'{mets}_x_pe'] = row[f'{mets}_y_pe']
                selected_rows.at[(idx_y, idx_x), f'{mets}_y_pe'] = row[f'{mets}_x_pe']
                selected_rows.at[(idx_y, idx_x), f'{mets}_x_svr (%)'] = row[f'{mets}_y_svr (%)']
                selected_rows.at[(idx_y, idx_x), f'{mets}_y_svr (%)'] = row[f'{mets}_x_svr (%)']
                selected_rows.at[(idx_y, idx_x), f'{mets}_x_bsr (%)'] = row[f'{mets}_y_bsr (%)']
                selected_rows.at[(idx_y, idx_x), f'{mets}_y_bsr (%)'] = row[f'{mets}_x_bsr (%)']
                selected_rows.at[(idx_y, idx_x), f'{mets}_x_prop (%)'] = row[f'{mets}_y_prop (%)']
                selected_rows.at[(idx_y, idx_x), f'{mets}_y_prop (%)'] = row[f'{mets}_x_prop (%)']
                selected_rows.at[(idx_y, idx_x), f'{mets}_x_prop_roc (%)'] = row[f'{mets}_y_prop_roc (%)']
                selected_rows.at[(idx_y, idx_x), f'{mets}_y_prop_roc (%)'] = row[f'{mets}_x_prop_roc (%)']

    # Use .loc to explicitly create a copy of the filtered rows
    selected_rows = selected_rows[selected_rows.index.get_level_values(0) == target_event].copy()

    int_columns = ['Count', 'total_sent']
    selected_rows[int_columns] = selected_rows[int_columns].astype(int)

    selected_rows = selected_rows.reset_index()
    selected_rows['type_y'] = selected_rows['type_y'].astype('category').cat.set_categories(ho_types)
    selected_rows = selected_rows.sort_values(by=['type_y']).reset_index(drop=True)
    selected_rows = selected_rows.set_index(['type_x', 'type_y'])
    # display(selected_rows)
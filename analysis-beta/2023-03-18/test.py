table = table_dr[['ho_type0_m','ho_type0_s','ho_count','dl_excl_m','dl_lost_mlss','dl_excl_mess']].copy()
table = table.query('ho_count > 0').reset_index(drop=True)
table.at[0, 'ho_count'] = 0
table['save_ratio'] = table['dl_excl_mess'] / (table['dl_excl_m'] + table['dl_lost_mlss']) * 100
t_excl = table.dl_excl_m.sum() + table.dl_lost_mlss.sum()
table['save_proportion'] = table['dl_excl_mess'] / t_excl * 100

print('Dual Radio Statistics: sort by DL excl per Event')
with pd.option_context('display.max_rows', None):
    table = table.sort_values(by=['save_proportion','save_ratio','dl_excl_m'], ascending=False).query('dl_excl_mess > 0').reset_index(drop=True).copy()
    display(table)
    display(table[table['ho_type0_m'] == 'NAS_Recovery_otherFailure (2)'])
    display(table[table['ho_type0_m'] == 'MCG_Failure_otherFailure (2)'])
    display(table[table['ho_type0_m'] == 'SN_Setup'])
    display(table[table['ho_type0_m'] == 'MN_HO'])
    display(table[table['ho_type0_m'] == 'SN_HO'])
    display(table[table['ho_type0_m'] == 'LTE_HO'])
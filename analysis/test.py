def cut_head_tail(df_HO, df, mode='ul'):
    if mode == 'ul':
        start = df.iloc[0].xmit_time
        stop = df.iloc[-1].xmit_time
        df_HO = df_HO.query('start >= @start & start <= @stop').copy().reset_index(drop=True)
    if mode == 'dl':
        start = df.iloc[0].arr_time
        stop = df.iloc[-1].arr_time
        df_HO = df_HO.query('start >= @start & start <= @stop').copy().reset_index(drop=True)
    return df_HO

def is_disjoint(set1, set2):
    """
    Check if two sets are disjoint.
    """
    return (set1 & set2).empty

def is_disjoint_dict(E):
    test_intv = P.empty()
    for key, val in E.items():
        # print(key)
        for intv in val:
            if is_disjoint(test_intv, intv.interval):
                test_intv = test_intv | intv.interval
            else:
                print(key, intv.index)
                return False
    return True

def interp(x, y, ratio):
    """
    Interpolation

    Args:
        x, y (datetime.datetime): x < y
        ratio (float): a decimal numeral in a range [0, 1]; 0 means break at x, 1 means break at y.
    Returns:
        (datetime.datetime): breakpoint of interpolation
    """
    return x + (y - x) * ratio

def get_ho_interval(df, sec=(1, 3), ratio=0.5,
                 ignored=['Conn_Setup','Conn_Rel'],
                 handover=['LTE_HO', 'MN_HO', 'MN_HO_SN_REL', 'SN_HO', 'SN_SU', 'SN_REL'],
                 linkfailure=['SCG_FAIL', 'MCG_FAIL', 'NAS_RECOV'],
                 ImpactScope=ImpactScope):
    
    HO_INTV = namedtuple('HO_INTV', 'index, interval, m_src, m_tgt, s_src, s_tgt, PCI, eNB_ID, Cell_ID, Band ID', defaults=tuple([None]*10))
    
    def ignore_col(row):
        if row.type in ignored:
            return False
        else:
            return True
    df = df[df.apply(ignore_col, axis=1)].reset_index(drop=True)
    
    column_names = []
    for type_name in handover + linkfailure:
        column_names += ["before_{}".format(type_name), "during_{}".format(type_name), "after_{}".format(type_name)]
    E = { col:[] for col in column_names }
    
    for i, row in df.iterrows():
        prior_row = df.iloc[i-1] if i != 0 else None
        post_row = df.iloc[i+1] if i != len(df)-1 else None
        ### peek the next event
        if i != len(df)-1 and pd.notna(row.end) and row.end > post_row.start:
            print(i, row.start, row.end, row.type, row.cause)
            print(i+1, post_row.start, post_row.end, post_row.type, post_row.cause)
            continue
        ### peri_interval
        if pd.isna(row.end):
            peri_interval = P.singleton(row.start)
        else:
            peri_interval = P.closed(row.start, row.end)
        ### prior_interval
        type_name = row.type if row.type not in ['SCG_FAIL', 'MCG_FAIL', 'NAS_RECOV'] else row.type + '_' + row.cause
        C = row.start - pd.Timedelta(seconds=ImpactScope[type_name][0])
        D = row.start
        prior_interval = P.closedopen(C, D)
        if ratio != None and i != 0:
            type_name = prior_row.type if prior_row.type not in ['SCG_FAIL', 'MCG_FAIL', 'NAS_RECOV'] else prior_row.type + '_' + prior_row.cause
            A = max(prior_row.start, prior_row.end)
            B = max(prior_row.start, prior_row.end) + pd.Timedelta(seconds=ImpactScope[type_name][1])
            if P.openclosed(A, B).overlaps(prior_interval):
                # print("Overlaps with the previous!")
                bkp = interp(C, B, ratio)
                bkp = max(bkp, A)  # to avoid the breakpoint overlaps the previous event's duration
                # bkp = min(max(bkp, A), D)  # 我不侵犯到其他任何人，代表其他人也不會侵犯到我！
                prior_interval = P.closedopen(bkp, D)
                if A in prior_interval:
                    prior_interval = P.open(bkp, D)
                # blindly set as open inverval is fine, but may miss one point.
        ### post_interval
        type_name = row.type if row.type not in ['SCG_FAIL', 'MCG_FAIL', 'NAS_RECOV'] else row.type + '_' + row.cause
        C = row.end
        D = row.end + pd.Timedelta(seconds=ImpactScope[type_name][1])
        post_interval = P.openclosed(C, D)
        if ratio != None and i != len(df)-1:
            type_name = post_row.type if post_row.type not in ['SCG_FAIL', 'MCG_FAIL', 'NAS_RECOV'] else post_row.type + '_' + post_row.cause
            A = min(post_row.start, post_row.end) - pd.Timedelta(seconds=ImpactScope[type_name][0])
            B = min(post_row.start, post_row.end)
            if P.closedopen(A, B).overlaps(post_interval):
                # print("Overlaps with the following!")
                bkp = interp(A, D, ratio)
                bkp = min(bkp, B)  # to avoid the breakpoint overlaps the following event's duration
                # bkp = max(min(bkp, B), C)  # 我不侵犯到其他任何人，代表其他人也不會侵犯到我！
                post_interval = P.open(C, bkp)
        ### append dictionary
        type_name = row.type if row.type not in ['SCG_FAIL', 'MCG_FAIL', 'NAS_RECOV'] else row.type + '_' + row.cause
        # state1, state2 = 'sn_change', 'sn_change'
        # if type_name in linkfailure:
        #     state1, state2 = 'link_failure', 'link_failure'
        # if type_name in ['LTE_HO','MN_HO','SN_Rel_MN_HO']:
        #     state1 = 'inter_freq' if row.sFreq != row.tFreq else 'intra_freq'
        #     if pd.notna(row.eNB) and pd.notna(row.eNB1) and row.eNB != row.eNB1:
        #         state2 = 'inter_enb'
        #     elif row.sPCI != row.tPCI:
        #         state2 = 'inter_sector'
        #     elif row.sPCI == row.tPCI:
        #         state2 = 'intra_sector'
        #     else:
        #         print("************** inter_enb, unknown eNB_ID **************")
        #         state2 = 'inter_enb'
        E[f'before_{type_name}'].append(HO_INTV(i, prior_interval, row.m_src, row.m_tgt, row.s_src, row.s_tgt, row.PCI, row.eNB_ID, row.Cell_ID, row['Band ID']))
        E[f'during_{type_name}'].append(HO_INTV(i, peri_interval, row.m_src, row.m_tgt, row.s_src, row.s_tgt, row.PCI, row.eNB_ID, row.Cell_ID, row['Band ID']))
        E[f'after_{type_name}'].append(HO_INTV(i, post_interval, row.m_src, row.m_tgt, row.s_src, row.s_tgt, row.PCI, row.eNB_ID, row.Cell_ID, row['Band ID']))
        ### check whether the intervals are pairwise disjoint
        if not is_disjoint_dict(E):
            print('Warning: Intervals are not totally disjoint!')
    return E

def label_ho_info(df, E, mode='ul'):
    def removeprefix(string, prefix=['before','during','after']):
        for pref in prefix:
            if string.startswith(pref):
                return pref, string[len(pref)+1:]
        return None, string
    
    df = df.reindex(columns=[*list(df.columns),
            'ho_index','ho_stage','ho_type','ho_m_src', 'ho_m_tgt', 'ho_s_src', 'ho_s_tgt', 'ho_PCI', 'ho_eNB_ID', 'ho_Cell_ID', 'ho_Band ID'])
    
    df[['ho_index', 'ho_stage', 'ho_type', 'ho_m_src', 'ho_m_tgt', 'ho_s_src', 'ho_s_tgt', 'ho_PCI', 'ho_eNB_ID', 'ho_Cell_ID', 'ho_Band ID']] = \
        [-1, '-', 'stable',  None, None, None, None, None, None, None, None]
            
    for key, val in E.items():
        pref, key = removeprefix(key)
        for intv in val:
            if intv.interval.empty:
                continue
            # print(pref, key)
            # print(intv.interval)
            if mode == 'ul':
                df.loc[(df['xmit_time'] >= intv.interval.lower) & (df['xmit_time'] <= intv.interval.upper),
                       ('ho_index', 'ho_stage', 'ho_type', 'ho_m_src', 'ho_m_tgt', 'ho_s_src', 'ho_s_tgt', 'ho_PCI', 'ho_eNB_ID', 'ho_Cell_ID', 'ho_Band ID')] = \
                        [intv.index, pref, key, intv.m_src, intv.m_tgt, intv.s_src, intv.s_tgt, intv.PCI, intv.eNB_ID, intv.Cell_ID, intv['Band ID']]
            if mode == 'dl':
                df.loc[(df['arr_time'] >= intv.interval.lower) & (df['arr_time'] <= intv.interval.upper),
                       ('ho_index', 'ho_stage', 'ho_type', 'ho_m_src', 'ho_m_tgt', 'ho_s_src', 'ho_s_tgt', 'ho_PCI', 'ho_eNB_ID', 'ho_Cell_ID', 'ho_Band ID')] = \
                        [intv.index, pref, key, intv.m_src, intv.m_tgt, intv.s_src, intv.s_tgt, intv.PCI, intv.eNB_ID, intv.Cell_ID, intv['Band ID']]
    
    # df['ho_type0'] = df['ho_type']
    # df.loc[np.in1d(df['ho_type'], ['SCG_Failure','MCG_Failure','NAS_Recovery']), 'ho_type0'] = \
    #     df.loc[np.in1d(df['ho_type'], ['SCG_Failure','MCG_Failure','NAS_Recovery']), 'ho_type'] + '_' + df.loc[np.in1d(df['ho_type'], ['SCG_Failure','MCG_Failure','NAS_Recovery']), 'ho_cause']
    
    # df['_ho_type'] = df['ho_type']
    # df['_ho_type0'] = df['ho_type0']
    # df['_ho_type1'] = df['ho_type1']
    # df['_ho_type2'] = df['ho_type2']
    # df.loc[~np.in1d(df['ho_type'], ['stable']), '_ho_type'] = df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_stage'] + '_' + df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_type']
    # df.loc[~np.in1d(df['ho_type'], ['stable']), '_ho_type0'] = df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_stage'] + '_' + df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_type0']
    # df.loc[~np.in1d(df['ho_type'], ['stable']), '_ho_type1'] = df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_stage'] + '_' + df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_type1']
    # df.loc[~np.in1d(df['ho_type'], ['stable']), '_ho_type2'] = df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_stage'] + '_' + df.loc[~np.in1d(df['ho_type'], ['stable']), 'ho_type2']
    
    # df['ho_index'] = df['ho_index'].astype('Int32')
    # df['ho_stage'] = df['ho_stage'].astype('category')
    # df['ho_type'] = df['ho_type'].astype('category')
    # df['ho_type0'] = df['ho_type0'].astype('category')
    # df['ho_type1'] = df['ho_type1'].astype('category')
    # df['ho_type2'] = df['ho_type2'].astype('category')
    # df['ho_scel'] = df['ho_scel'].astype('Int8')
    # df['ho_cause'] = df['ho_cause'].astype('category')
    # df['ho_intr'] = df['ho_intr'].astype('float32')
    # for tag in df.columns[df.columns.get_loc('ho_ePCI'):df.columns.get_loc('ho_nrPCI1')+1]:
    #     df[tag] = df[tag].astype('Int32')
    # df['_ho_type'] = df['_ho_type'].astype('category')
    # df['_ho_type0'] = df['_ho_type'].astype('category')
    # df['_ho_type1'] = df['_ho_type1'].astype('category')
    # df['_ho_type2'] = df['_ho_type2'].astype('category')
    
    return df
sorter = ['LTE_HO','MN_HO','SN_HO','MNSN_HO','SN_Rel','SN_Setup','SN_Rel_MN_HO','SN_Setup_MN_HO',
          'SCG_Failure_t310-Expiry (0)','SCG_Failure_randomAccessProblem (1)','SCG_Failure_rlc-MaxNumRetx (2)','SCG_Failure_synchReconfigFailureSCG (3)',
          'SCG_Failure_scg-ReconfigFailure (4)','SCG_Failure_srb3-IntegrityFailure (5)','SCG_Failure_other-r16 (6)',
          'MCG_Failure_reconfigurationFailure (0)','MCG_Failure_handoverFailure (1)','MCG_Failure_otherFailure (2)',
          'NAS_Recovery_reconfigurationFailure (0)','NAS_Recovery_handoverFailure (1)','NAS_Recovery_otherFailure (2)']

D = {}
for tag in sorter:
    D[tag] = {'tables': [], 'intrs': [], 'count': []}

for (exp, traces), devices, schemes in zip(exps.items(), _devices, _schemes):
    for trace in traces:
        for j, (dev, schm) in enumerate(zip(devices, schemes)):
            ## read downlink
            data = os.path.join(datadir, exp, dev, trace, 'data', 'udp_uplk_loss_latency.csv')
            print(data, os.path.isfile(data))
            df_ul = pd.read_csv(data)
            df_ul = set_data(df_ul)
            ## read handover
            path = os.path.join(datadir, exp, dev, trace, 'data')
            data = os.path.join(path, [s for s in os.listdir(path) if s.startswith('diag_log_') and s.endswith('_rrc.csv')][0])
            print(data, os.path.isfile(data))
            df_ho = pd.read_csv(data)
            df_ho, _, _ = mi_parse_ho(df_ho, tz=8)
            df_ho['ho_type0'] = df_ho['ho_type'].astype('string')
            df_ho.loc[df_ho['cause'].notna(), 'ho_type0'] = df_ho['ho_type'].astype('string') + '_' + df_ho['cause'].astype('string')
            df_ho['ho_type0'] = df_ho['ho_type0'].astype('category')
            ## start processing
            for tag in sorter:
                # print('===================================')
                # print(tag)
                df = df_ho.query('ho_type0 == @tag').copy().reset_index(drop=True)
                tables = []
                intrs = []
                if not df.empty:
                    cname = ' '.join(df.at[0, 'ho_type'].split('_')) + ': ' + df.at[0, 'cause'] if pd.notna(df.at[0, 'cause']) else ' '.join(df.at[0, 'ho_type'].split('_'))
                    for i, row in df.iterrows():
                        start, end = df.at[i, 'start'], df.at[i, 'end']
                        intr = df.at[i, 'intr'] if pd.notna(df.at[i, 'intr']) else 0
                        table, intv = setup_profile(df_ul, start, end, mode='pyl', sec=10)
                        # print(intr)
                        # display(table)
                        tables.append(table)
                        intrs.append(intr)
                    table, intr = merge_profile(tables, intrs)
                    # print('Avg Duration:', intr, 'seconds')
                    # display(table)
                    # plot_profile(table, intr=intr, title=cname, mode='lost')
                    # plot_profile(table, intr=intr, title=cname, mode='plr')
                else:
                    table = pd.DataFrame(columns=['cat_id','tx_count','lost','PLR'])
                    table['cat_id'] = table['cat_id'].astype('float32')
                    table['tx_count'] = table['tx_count'].astype('Int32')
                    table['lost'] = table['lost'].astype('Int32')
                    table['PLR'] = table['PLR'].astype('float32')
                    intr = 0
                # print('HO Count:', len(df))
                D[tag]['tables'].append(table)
                D[tag]['intrs'] = [*D[tag]['intrs'], *intrs]
                D[tag]['count'].append(len(df))
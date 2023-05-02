sorter = ['LTE_HO','MN_HO','SN_HO','MNSN_HO','SN_Rel','SN_Setup','SN_Rel_MN_HO','SN_Setup_MN_HO',
          'SCG_Failure_t310-Expiry (0)','SCG_Failure_randomAccessProblem (1)','SCG_Failure_rlc-MaxNumRetx (2)','SCG_Failure_synchReconfigFailureSCG (3)',
          'SCG_Failure_scg-ReconfigFailure (4)','SCG_Failure_srb3-IntegrityFailure (5)','SCG_Failure_other-r16 (6)',
          'MCG_Failure_reconfigurationFailure (0)','MCG_Failure_handoverFailure (1)','MCG_Failure_otherFailure (2)',
          'NAS_Recovery_reconfigurationFailure (0)','NAS_Recovery_handoverFailure (1)','NAS_Recovery_otherFailure (2)']

U = {}
for tag in sorter:
    U[tag] = {'tables': [], 'intrs': [], 'count': []}
ul_stable_pkt = 0
ul_stable_loss = 0
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
            df = df_ho[~np.in1d(df_ho['ho_type'], ['Conn_Setup', 'Conn_Rel'])].copy().reset_index(drop=True)
            A = {}
            for tag in sorter:
                A[tag] = {'tables': [], 'intrs': []}
            _intv = P.singleton(pd.Timestamp.min)
            for i, row in df.iterrows():
                prior_row = df.iloc[i-1] if i != 0 else None
                post_row = df.iloc[i+1] if i != len(df)-1 else None
                ### peek the next event: avoid MN/LTE HO overlaps with handoverFailure
                if i != len(df)-1 and pd.notna(row.end) and row.end > post_row.start:
                    print(i, row.start, row.end, row.ho_type, row.cause)
                    print(i+1, post_row.start, post_row.end, post_row.ho_type, post_row.cause)
                    continue
                if i != 0 and pd.notna(prior_row.end) and prior_row.end > row.start:
                    prior_row = df.iloc[i-2] if i > 1 else None
                ### basic timestamp
                tag = row.ho_type0
                start, end = row.start, row.end
                intr = row.intr if pd.notna(row.intr) else 0
                ### set left, right limit
                if prior_row is not None:
                    if pd.notna(prior_row.end):
                        # left = prior_row.end
                        left = prior_row.end + (start - prior_row.end) / 2
                    else:
                        # left = prior_row.start
                        left = prior_row.start + (start - prior_row.start) / 2
                else:
                    left = pd.Timestamp.min
                if post_row is not None:
                    if pd.notna(end):
                        # right = post_row.start
                        right = end + (post_row.start - end) / 2
                    else:
                        # right = post_row.start
                        right = start + (post_row.start - start) / 2
                else:
                    right = pd.Timestamp.max
                ### Setup profile
                table, intv = setup_profile(df_ul, tag, start, end, mode='ul', left=left, right=right)
                # print(intr)
                # display(table)
                A[tag]['tables'].append(table)
                A[tag]['intrs'].append(intr)
                ### count stable loss, pkt (1)
                if i == 0:
                    lower = pd.Timestamp.min
                    upper = intv.lower
                else:
                    lower = _intv.upper
                    upper = intv.lower
                df_tmp = df_ul.query('xmit_time > @lower & xmit_time <= @upper').copy().reset_index(drop=True)
                ul_stable_pkt += len(df_tmp)
                ul_stable_loss += sum(df_tmp['lost'])
                _intv = intv
            ### count stable loss, pkt (2)
            lower = _intv.upper
            upper = pd.Timestamp.max
            df_tmp = df_ul.query('xmit_time > @lower & xmit_time <= @upper').copy().reset_index(drop=True)
            ul_stable_pkt += len(df_tmp)
            ul_stable_loss += sum(df_tmp['lost'])
            for tag in sorter:
                if len(A[tag]['tables']) == 0:
                    continue
                table, intr = merge_profile(A[tag]['tables'], A[tag]['intrs'])
                # print('HO Count:', len(df))
                U[tag]['tables'].append(table)
                U[tag]['intrs'] = [*U[tag]['intrs'], *A[tag]['intrs']]
                U[tag]['count'].append(len(A[tag]['tables']))
            ul_stable_plr = ul_stable_loss / (ul_stable_pkt + 1e-9) * 100
            print(ul_stable_loss, ul_stable_pkt, round(ul_stable_plr, 3))
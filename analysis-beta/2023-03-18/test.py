for date, traces in dates.items():
    for trace in traces:
        i += 1
        dfs_ho.append([])
        st, et = [], []
        for j, (dev, schm) in enumerate(zip(devices, schemes)):
            data = os.path.join(datadir, date, exp, dev, trace, 'data', 'udp_uplk_loss_latency.csv')
            df = pd.read_csv(data)
            df = set_data(df)
            dfs_ho[i].append(df.copy())
            st.append(df['seq'].array[0])
            et.append(df['seq'].array[-1])
        st, et = max(st), min(et)
        for j, (dev, schm) in enumerate(zip(devices, schemes)):
            dfs_ho[i][j] = dfs_ho[i][j][(dfs_ho[i][j]['seq'] >= st) & (dfs_ho[i][j]['seq'] <= et)].reset_index(drop=True)
print(len(dfs_ho))
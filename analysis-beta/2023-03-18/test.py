if not (dfs_dl[i][x[0]].empty or dfs_dl[i][x[1]].empty):
            df_dl = pd.merge(dfs_dl[i][x[0]].copy(), dfs_dl[i][x[1]].copy(), on=['seq'], suffixes=('_m','_s')).copy()
            df_dl['latency_ms'] = df_dl[['latency_m', 'latency_s']].values.min(axis=1)
            avg_l_dl = round(df_dl[~(df_dl.lost_m & df_dl.lost_s)].latency_ms.mean(), 6)
            std_l_dl = round(df_dl[~(df_dl.lost_m & df_dl.lost_s)].latency_ms.std(), 6)
            jitter_dl = round(df_dl.loc[~(df_dl.lost_m & df_dl.lost_s), 'latency_ms'].diff().abe().mean(), 6)
        else:
            avg_l_dl, std_l_dl, jitter_dl = np.nan, np.nan, np.nan
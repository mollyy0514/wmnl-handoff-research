st_seq = max([dfs[key][0]['seq'].array[0], dfs[key][1]['seq'].array[0]])
    ed_seq = min([dfs[key][0]['seq'].array[-1], dfs[key][1]['seq'].array[-1]])
    dfs[key][0] = dfs[key][0][(dfs[key][0]['seq'] >= st_seq) & (dfs[key][0]['seq'] <= ed_seq)].reset_index(drop=True)
    dfs[key][1] = dfs[key][1][(dfs[key][1]['seq'] >= st_seq) & (dfs[key][1]['seq'] <= ed_seq)].reset_index(drop=True)
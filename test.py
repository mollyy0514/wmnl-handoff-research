df1 = dfs['nr'][0].copy()
df2 = dfs['nr'][1].copy()

df1 = df1[df1['serv_cel_index'] == 'PSCell'][['Timestamp', 'PCI', 'NR_ARFCN', 'RSRP', 'RSRQ']].reset_index(drop=True)
df2 = df2[df2['serv_cel_index'] == 'PSCell'][['Timestamp', 'PCI', 'NR_ARFCN', 'RSRP', 'RSRQ']].reset_index(drop=True)

axes[10].plot([], [], color='tab:red', alpha=0.7, label='nr_rsrp_radio1')
axes[10].plot([], [], color='tab:green', alpha=0.7, label='nr_rsrp_radio2')

ax_twinx = axes[10].twinx()
ax_twinx.plot(df1['Timestamp'], df1['RSRP'], color='tab:red', alpha=0.7, label='nr_rsrp_radio1')
ax_twinx.plot(df2['Timestamp'], df2['RSRP'], color='tab:green', alpha=0.7, label='nr_rsrp_radio2')
ax_twinx.set_ylim(-156, -31)
ax_twinx.axhline(y=-110, color='gray', linestyle='--', linewidth=1.1)

def drop_unchanged(df):
    
    df['prev_PCI'] = df['PCI'].shift(1)
    df['prev_NR_ARFCN'] = df['NR_ARFCN'].shift(1)
    df['handover'] = (df['PCI'] != df['prev_PCI']) | (df['NR_ARFCN'] != df['prev_NR_ARFCN'])
    df.loc[0, 'handover'] = True
    
    df = df[df['handover']].reset_index(drop=True).drop(['prev_PCI', 'prev_NR_ARFCN'], axis=1)
    df['duplicate'] = df.duplicated(subset=['PCI', 'NR_ARFCN'])
    
    pairs = [(pci, earfcn) for pci, earfcn in zip(df[~df['duplicate']]['PCI'].array, df[~df['duplicate']]['NR_ARFCN'].array)]
    
    return df, pairs

def drop_duplicate(my_list):
    unique_list = []
    seen = set()
    
    for item in my_list:
        if item not in seen:
            unique_list.append(item)
            seen.add(item)

    return unique_list

df1, pairs1 = drop_unchanged(df1)
df2, pairs2 = drop_unchanged(df2)

df = pd.concat([df1, df2], ignore_index=True).sort_values(by='Timestamp').reset_index(drop=True)
pairs = [(pci, earfcn) for pci, earfcn in zip(df[~df['duplicate']]['PCI'].array, df[~df['duplicate']]['NR_ARFCN'].array)]

cmap = plt.get_cmap('jet', len(pairs1))
colors = [matplotlib.colors.to_hex(cmap(i)) for i in range(cmap.N)]
cdict1 = {pair: color for pair, color in zip(pairs1, colors)}

cmap = plt.get_cmap('gist_rainbow', len(pairs2))
colors = [matplotlib.colors.to_hex(cmap(i)) for i in range(cmap.N)]
cdict2 = {pair: color for pair, color in zip(pairs2, colors)}

markers = ['p', '*', 'h', 'H', 'D', 'd', 'P', 'X']
mdict = {}  

axes[10].set_ylim(0, 1)
axes[10].set_yticks([0.25, 0.75])
axes[10].set_yticklabels(["Radio-1", "Radio-2"], rotation='vertical', va='center')

k = 0       
for pair in pairs1:
    pci_earfcn = f'{pair[0]}:{pair[1]}'
    
    df = df1.copy()
    tmp = df[(df['PCI'] == pair[0]) & (df['NR_ARFCN'] == pair[1])].reset_index(drop=True)
    if not tmp.empty:
        axes[10].vlines(tmp.Timestamp, ymin=0, ymax=0.55, color=cdict1[pair], linewidth=0.7, alpha=0.85, label=f'r1 {pci_earfcn}')
    
    tmp = tmp.drop(df.index[0])
    if not tmp.empty:
        axes[10].scatter(tmp.Timestamp, [0.05]*len(tmp), c=cdict1[pair], marker=markers[k % len(markers)], label=f'r1 {pci_earfcn} dup')
        k += 1

for pair in pairs2:
    pci_earfcn = f'{pair[0]}:{pair[1]}'
    
    df = df2.copy()
    tmp = df[(df['PCI'] == pair[0]) & (df['NR_ARFCN'] == pair[1])].reset_index(drop=True)
    if not tmp.empty:
        axes[10].vlines(tmp.Timestamp, ymin=0.45, ymax=1, color=cdict2[pair], linewidth=0.7, alpha=0.85, label=f'r2 {pci_earfcn}')
    
    tmp = tmp.drop(df.index[0])
    if not tmp.empty:
        axes[10].scatter(tmp.Timestamp, [0.95]*len(tmp), c=cdict2[pair], marker=markers[k % len(markers)], label=f'r2 {pci_earfcn} dup')
        k += 1
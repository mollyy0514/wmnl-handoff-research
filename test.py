# *********************************** HO ***********************************
ho_types = ['LTEH', 'ENBH', 'MCGH', 'MNBH', 'SCGM',
            'SCGA', 'SCGR-I', 'SCGC-I', 'SCGR-II', 'SCGC-II']

df_ho = sr_table_ul[np.in1d(sr_table_ul.index.get_level_values(0), ho_types)].copy().reset_index()
df_ho['type'] = df_ho['type'].astype('category').cat.set_categories(ho_types)
df_ho = df_ho.sort_values(by=['type', 'stage']).reset_index(drop=True)

# *********************************** Loss Rate ***********************************
event_frequency = df_ho.loc[df_ho['stage'] == '-', 'Frequency (/hr)'].to_list()
before_event_loss_rate = df_ho.loc[df_ho['stage'] == 'before', 'lost_r (%)'].to_list()
during_event_loss_rate = df_ho.loc[df_ho['stage'] == 'during', 'lost_r (%)'].to_list()
after_event_loss_rate = df_ho.loc[df_ho['stage'] == 'after', 'lost_r (%)'].to_list()
stable_loss_rate = sr_table_ul.at[('stable', '-'), 'lost_r (%)']

x = np.arange(len(ho_types))  # the label locations
width = 0.2  # the width of the bars
space = 0.55

fig, ax = plt.subplots(figsize=(6, 4))
rects1 = ax.bar(x - space/3, before_event_loss_rate, width, label='Before')
rects2 = ax.bar(x          , during_event_loss_rate, width, label='During')
rects3 = ax.bar(x + space/3, after_event_loss_rate, width, label='After')
ax.axhline(stable_loss_rate, c = 'tab:pink', linestyle='--', linewidth=1, label='Stable PLR')
ax.set_ylim(bottom=0)

xlim = ax.get_xlim()[0]
ax.text(1.478*xlim, stable_loss_rate, '{:.2f}'.format(stable_loss_rate), ha='center', fontweight='bold', fontsize=10, color='tab:pink')

for k, v in enumerate(event_frequency):
    if v == 0:
        ax.text(k, 0, "N/A", ha='center', va='bottom', color='blue', fontweight='bold')

# Add text for title and custom x-axis tick labels, etc.
ax.set_ylabel('Packet Loss Rate (%)')
ax.set_title('Uplink PLR (HO): Airport Line')
ax.legend()

ax.set_xticks(x, ho_types)
ax.set_xticklabels(ax.get_xticklabels(), rotation=40, fontsize=9.5, ha="right")

fig.tight_layout()
plt.show()

# *********************************** Loss Per Event ***********************************
event_frequency = df_ho.loc[df_ho['stage'] == '-', 'Frequency (/hr)'].to_list()
loss_per_event = df_ho.loc[df_ho['stage'] == '-', 'lost_pe'].to_list()

x = np.arange(len(ho_types))  # the label locations
width = 0.5  # the width of the bars
space = 0.55

fig, ax = plt.subplots(figsize=(6, 4))
rect = ax.bar(x, loss_per_event, width, color='tab:orange', alpha=0.85)
ax.set_ylim(bottom=0)

ax_twin = ax.twinx()
ax_twin.plot(x, event_frequency, linestyle='-', color='none', marker='o', mfc='blue', mec='blue', markersize=4)
ax_twin.plot([], [], linestyle='-', color='blue', marker='o', mfc='blue', mec='blue', markersize=4, label='Event Occurrence', linewidth=1)
rect = ax_twin.bar(x, event_frequency, width=0.03, color='blue')
ax_twin.set_ylabel('Frequency (/hr)')

ax_twin.set_ylim(bottom=0)
ax_twin.set_ylim(top=ax_twin.get_ylim()[1]*1.02)
ylim = ax_twin.get_ylim()[1]

for k, v in enumerate(event_frequency):
    if v == 0:
        ax.text(k, 0, "N/A", ha='center', va='bottom', color='blue', fontweight='bold')
    else:
        ax_twin.text(k, v + 0.01*ylim, '{:.2f}'.format(v), ha='center', va='bottom', color='blue', fontweight='bold', fontsize=9.5)

# Add text for title and custom x-axis tick labels, etc.
ax.set_ylabel('Loss Per Event')
ax.set_title('Uplink LPE (HO): Airport Line')
ax_twin.legend()

ax.set_xticks(x, ho_types)
ax.set_xticklabels(ax.get_xticklabels(), rotation=40, fontsize=9.5, ha="right")

fig.tight_layout()
plt.show()

# *********************************** RLF ***********************************
rlf_types = ['NASR', 'MCGF', 'SCGF']

df_rlf = sr_table_ul[np.in1d(sr_table_ul.index.get_level_values(0), rlf_types)].copy().reset_index()
df_rlf['type'] = df_rlf['type'].astype('category').cat.set_categories(rlf_types)
df_rlf = df_rlf.sort_values(by=['type', 'stage']).reset_index(drop=True)

# *********************************** Loss Rate ***********************************
event_frequency = df_rlf.loc[df_rlf['stage'] == '-', 'Frequency (/hr)'].to_list()
before_event_loss_rate = df_rlf.loc[df_rlf['stage'] == 'before', 'lost_r (%)'].to_list()
during_event_loss_rate = df_rlf.loc[df_rlf['stage'] == 'during', 'lost_r (%)'].to_list()
after_event_loss_rate = df_rlf.loc[df_rlf['stage'] == 'after', 'lost_r (%)'].to_list()
stable_loss_rate = sr_table_ul.at[('stable', '-'), 'lost_r (%)']

x = np.arange(len(rlf_types))  # the label locations
width = 0.2  # the width of the bars
space = 0.55

fig, ax = plt.subplots(figsize=(3, 4))
rects1 = ax.bar(x - space/3, before_event_loss_rate, width, label='Before')
rects2 = ax.bar(x          , during_event_loss_rate, width, label='During')
rects3 = ax.bar(x + space/3, after_event_loss_rate, width, label='After')
ax.axhline(stable_loss_rate, c = 'tab:pink', linestyle='--', linewidth=1, label='Stable PLR')
ax.set_ylim(bottom=0)

xlim = ax.get_xlim()[0]
ax.text(1.478*xlim, stable_loss_rate, '{:.2f}'.format(stable_loss_rate), ha='center', fontweight='bold', fontsize=10, color='tab:pink')

for k, v in enumerate(event_frequency):
    if v == 0:
        ax.text(k, 0, "N/A", ha='center', va='bottom', color='blue', fontweight='bold')

# Add text for title and custom x-axis tick labels, etc.
ax.set_ylabel('Packet Loss Rate (%)')
ax.set_title('Uplink PLR (RLF): Airport Line')
ax.legend()

ax.set_xticks(x, rlf_types)
ax.set_xticklabels(ax.get_xticklabels(), rotation=40, fontsize=9.5, ha="right")

fig.tight_layout()
plt.show()

# *********************************** Loss Per Event ***********************************
event_frequency = df_rlf.loc[df_rlf['stage'] == '-', 'Frequency (/hr)'].to_list()
loss_per_event = df_rlf.loc[df_rlf['stage'] == '-', 'lost_pe'].to_list()

x = np.arange(len(rlf_types))  # the label locations
width = 0.5  # the width of the bars
space = 0.55

fig, ax = plt.subplots(figsize=(3, 4))
rect = ax.bar(x, loss_per_event, width, color='tab:orange', alpha=0.85)
ax.set_ylim(bottom=0)

ax_twin = ax.twinx()
ax_twin.plot(x, event_frequency, linestyle='-', color='none', marker='o', mfc='blue', mec='blue', markersize=4)
ax_twin.plot([], [], linestyle='-', color='blue', marker='o', mfc='blue', mec='blue', markersize=4, label='Event Occurrence', linewidth=1)
rect = ax_twin.bar(x, event_frequency, width=0.03, color='blue')
ax_twin.set_ylabel('Frequency (/hr)')

ax_twin.set_ylim(bottom=0)
ax_twin.set_ylim(top=ax_twin.get_ylim()[1]*1.02)
ylim = ax_twin.get_ylim()[1]

for k, v in enumerate(event_frequency):
    if v == 0:
        ax.text(k, 0, "N/A", ha='center', va='bottom', color='blue', fontweight='bold')
    else:
        ax_twin.text(k, v + 0.01*ylim, '{:.2f}'.format(v), ha='center', va='bottom', color='blue', fontweight='bold', fontsize=9.5)

# Add text for title and custom x-axis tick labels, etc.
ax.set_ylabel('Loss Per Event')
ax.set_title('Uplink LPE (RLF): Airport Line')
# ax_twin.legend()

ax.set_xticks(x, rlf_types)
ax.set_xticklabels(ax.get_xticklabels(), rotation=40, fontsize=9.5, ha="right")

fig.tight_layout()
plt.show()
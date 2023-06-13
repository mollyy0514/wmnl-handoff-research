_schms = ['All','LTE','B1','B3','B7','B8','B1B3','B1B7','B1B8','B3B7','B3B8','B7B8']

xs = list(it.product(_schms, repeat=2))
xs = ['+'.join([s[0], s[1]]) for s in xs]
xs = np.reshape(xs, (len(_schms), len(_schms)))
mtags = masked(xs.tolist(), mask(len(_schms), mode='upper'))

mat = fill_out_matrix(_schms, mtags, dl_plr_dict)
ax = sns.heatmap(mat.T, annot=True, fmt='.2g', mask=mask(len(_schms)), annot_kws={"size": 6})
ax.set_title(f'Uplink PLR (%)')
plt.show()
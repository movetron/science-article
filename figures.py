import json, math, statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

R = json.load(open('results.json'))
plt.rcParams.update({'font.family': 'DejaVu Serif', 'font.size': 10, 'axes.spines.top': False,
                     'axes.spines.right': False, 'axes.grid': True, 'grid.color': '#dddddd',
                     'grid.linewidth': 0.6, 'axes.axisbelow': True, 'savefig.dpi': 220,
                     'legend.frameon': False})
C = {'LL(1)': '#2a78d6', 'SLR(1)': '#eb6834', 'LALR(1)': '#1baf7a', 'LR(1)': '#eda100',
     'ОП (матрица)': '#e87ba4', 'ОП (функции)': '#008300', 'LALR(1)+DR': '#1baf7a'}
HATCH = {'LL(1)': '', 'SLR(1)': '//', 'LALR(1)': '..', 'LR(1)': 'xx', 'ОП (матрица)': '\\\\',
         'ОП (функции)': '--', 'LALR(1)+DR': 'oo'}
MK = {'LL(1)': 'o', 'SLR(1)': 's', 'LALR(1)': '^', 'LR(1)': 'D', 'ОП (матрица)': 'v', 'ОП (функции)': 'P'}


def save(name):
    plt.tight_layout(); plt.savefig(f'fig/{name}.png', facecolor='white'); plt.close()


import os; os.makedirs('fig', exist_ok=True)

# ---- Рис.1 схема стенда
fig, ax = plt.subplots(figsize=(7.4, 2.9)); ax.axis('off'); ax.set_xlim(0, 10.1); ax.set_ylim(1.0, 4.7)
def box(x, y, w, h, t, fc='#eef4fc'):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.05,rounding_size=0.12', fc=fc, ec='#333', lw=0.9))
    ax.text(x + w / 2, y + h / 2, t, ha='center', va='center', fontsize=8.5)
def arr(x1, y1, x2, y2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle='->', lw=0.9, color='#333'))
box(0.1, 3.4, 2.0, 1.2, 'Грамматики\nG1–G7, L$_k$\n+ корпуса A, B')
box(0.1, 1.2, 2.0, 1.2, 'Преобразование\nк LL(1): алгоритм\nПола + факторизация', '#fdf1e9')
box(2.85, 3.4, 2.65, 1.2, 'Построение таблиц:\nLL(1), SLR(1), LALR(1),\nLR(1), ОП (матрица/функции)')
box(2.9, 1.2, 2.4, 1.2, 'Генератор цепочек\n(вывод с бюджетом длины)\n+ мутации del/ins/rep/swap')
box(6.0, 3.4, 1.8, 1.2, 'Единый\nдрайвер\nразбора')
box(6.0, 1.2, 1.9, 1.2, 'Эталон:\nканоническое\nLR(1)', '#eaf7f1')
box(8.4, 2.3, 1.5, 1.2, 'Метрики:\nМ1–М6', '#fff6df')
arr(2.1, 4.0, 2.9, 4.0); arr(1.1, 3.4, 1.1, 2.4); arr(2.1, 1.8, 2.9, 3.6)
arr(5.5, 4.0, 6.0, 4.0); arr(5.3, 1.8, 6.0, 3.6); arr(5.3, 1.8, 6.0, 1.8)
arr(7.8, 4.0, 8.4, 3.2); arr(7.8, 1.8, 8.4, 2.6)
save('fig1_scheme')

# ---- Рис.2 размер таблиц
E1 = R['E1']; gl = ['G1', 'G3', 'G5', 'G6', 'G7']
meths = ['LL(1)', 'SLR(1)', 'LALR(1)', 'LALR(1)+DR', 'LR(1)', 'ОП (матрица)', 'ОП (функции)']
def filled(g, m):
    v = E1[g]
    if m == 'LL(1)':
        if v['LL']['conflicts'] == 0: return v['LL']['filled']
        t = v['LL_transformed']; return t['filled'] if t and t['conflicts'] == 0 else None
    if m == 'SLR(1)': return v['SLR']['filled'] if v['SLR']['conflicts'] == 0 else None
    if m == 'LALR(1)': return v['LALR']['filled']
    if m == 'LALR(1)+DR': return v['LALR_DR_filled']
    if m == 'LR(1)': return v['LR1']['filled']
    if m == 'ОП (матрица)': return v['OP']['filled'] if v['OP'] and v['OP']['conflicts'] == 0 else None
    if m == 'ОП (функции)': return v['OP']['filled'] and 2 * (v['size']['T'] + 1) if v['OP'] and v['OP_funcs'] else None
fig, ax = plt.subplots(figsize=(7.2, 3.6))
w = 0.12; x = np.arange(len(gl))
for i, m in enumerate(meths):
    ys = [filled(g, m) for g in gl]
    for j, y in enumerate(ys):
        if y is None:
            ax.text(x[j] + (i - 3) * w, 7, '×', ha='center', va='bottom', fontsize=8, color='#777')
    ax.bar(x + (i - 3) * w, [y or 0 for y in ys], w * 0.92, color=C[m], hatch=HATCH[m], edgecolor='white', lw=0.4, label=m)
ax.set_yscale('log'); ax.set_ylim(5, 4000)
short = {'G1': 'выражения', 'G3': 'указатели', 'G5': 'JSON', 'G6': 'PL/0', 'G7': 'подмн. C'}
ax.set_xticks(x, [f"{g}\n{short[g]}" for g in gl], fontsize=8.5)
ax.set_ylabel('Значимых элементов таблиц (лог. шкала)')
ax.legend(ncol=4, fontsize=7.5, loc='upper left')
save('fig2_tables')

# ---- Рис.3 корпус A: доля по размеру
A = R['E2']['A']
bins = [(3, 6), (7, 10), (11, 14), (15, 18), (19, 30)]
ms = [('LL', 'LL(1)'), ('LLt', 'LL(1) после преобр.'), ('SLR', 'SLR(1)'), ('LALR', 'LALR(1)'), ('LR1', 'LR(1)'), ('OP', 'ОП')]
cmap = {'LL': C['LL(1)'], 'LLt': C['LL(1)'], 'SLR': C['SLR(1)'], 'LALR': C['LALR(1)'], 'LR1': C['LR(1)'], 'OP': C['ОП (матрица)']}
fig, ax = plt.subplots(figsize=(7.0, 3.6))
xs = np.arange(len(bins))
for key, lab in ms:
    ys = []
    for lo, hi in bins:
        sub = [a for a in A if lo <= a['P'] <= hi]
        ys.append(100 * sum(a[key] for a in sub) / len(sub))
    ls = '--' if key in ('LLt', 'LR1') else '-'
    mk = {'LL': 'o', 'LLt': 'o', 'SLR': 's', 'LALR': '^', 'LR1': 'D', 'OP': 'v'}[key]
    ax.plot(xs, ys, ls, marker=mk, ms=6 if key != 'LR1' else 8, mfc='white' if key in ('LLt', 'LR1') else cmap[key],
            color=cmap[key], lw=2, label=lab)
ax.set_xticks(xs, [f'{lo}–{hi}\n(n={sum(1 for a in A if lo <= a["P"] <= hi)})' for lo, hi in bins])
ax.set_xlabel('Число правил грамматики |P|'); ax.set_ylabel('Доля грамматик без конфликтов, %')
ax.legend(ncol=3, fontsize=8)
save('fig3_corpusA')

# ---- Рис.4 корпус B: пересечения ОП и LR(1)
B = R['E2']['B']
cats = {'ОП и LR(1)': sum(b['OP'] and b['LR1'] for b in B), 'только ОП': sum(b['OP'] and not b['LR1'] for b in B),
        'только LR(1)': sum(b['LR1'] and not b['OP'] for b in B), 'ни один': sum(not b['OP'] and not b['LR1'] for b in B)}
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.2), gridspec_kw={'width_ratios': [1.25, 1]})
ax = axs[0]
keys = [('LL', 'LL(1)'), ('LLt', 'LL(1)*'), ('SLR', 'SLR(1)'), ('LALR', 'LALR(1)'), ('LR1', 'LR(1)'), ('OP', 'ОП'), ('OPfun', 'ОП-функц.')]
vals = [100 * sum(b[k] for b in B) / len(B) for k, _ in keys]
cols = [C['LL(1)'], C['LL(1)'], C['SLR(1)'], C['LALR(1)'], C['LR(1)'], C['ОП (матрица)'], C['ОП (функции)']]
bars = ax.bar(range(len(keys)), vals, color=cols, edgecolor='white', hatch=['', '//', '', '', '', '', ''])
for b_, v in zip(bars, vals):
    ax.text(b_.get_x() + b_.get_width() / 2, v + 0.8, f'{v:.1f}', ha='center', fontsize=7.5)
ax.set_xticks(range(len(keys)), [l for _, l in keys], fontsize=7.5, rotation=20)
ax.set_ylabel('Доля грамматик, %'); ax.set_title('а) корпус B (n = %d)' % len(B), fontsize=9)
ax = axs[1]
cv = list(cats.values()); cl = list(cats.keys())
ax.barh(range(4), cv, color=['#8a8a8a', C['ОП (матрица)'], C['LR(1)'], '#d9d9d9'], edgecolor='white')
for i, v in enumerate(cv):
    ax.text(v + 15, i, str(v), va='center', fontsize=8)
ax.set_yticks(range(4), cl, fontsize=8); ax.invert_yaxis(); ax.set_xlim(0, max(cv) * 1.2)
ax.set_xlabel('Число грамматик'); ax.set_title('б) ОП против LR(1)', fontsize=9)
save('fig4_corpusB')

# ---- Рис.5 масштабирование
E5 = R['E5']; k = [r['k'] for r in E5]
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.3))
ax = axs[0]
ax.plot(k, [r['n0'] for r in E5], '-^', color=C['LALR(1)'], lw=2, label='SLR(1) / LALR(1)')
ax.plot(k, [r['n1'] for r in E5], '-D', color=C['LR(1)'], lw=2, label='LR(1)')
ax.set_xlabel('Число уровней приоритета k'); ax.set_ylabel('Число состояний'); ax.set_title('а) состояния автомата', fontsize=9)
ax.legend(fontsize=8)
ax = axs[1]
for key, lab, c, m in [('t_ll', 'LL(1)', C['LL(1)'], 'o'), ('t_op', 'ОП', C['ОП (матрица)'], 'v'), ('t_slr', 'SLR(1)', C['SLR(1)'], 's'),
                       ('t_lalr', 'LALR(1)', C['LALR(1)'], '^'), ('t_lr1', 'LR(1)', C['LR(1)'], 'D')]:
    ax.plot(k, [r[key] for r in E5], '-' + m, color=c, lw=2, ms=5, label=lab)
ax.set_yscale('log'); ax.set_xlabel('Число уровней приоритета k'); ax.set_ylabel('Время построения, мс (лог.)')
ax.set_title('б) время построения таблиц', fontsize=9); ax.legend(fontsize=7.5, ncol=2)
save('fig5_scaling')

# ---- Рис.6 скорость
E3 = R['E3']
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.3))
ax = axs[0]
for m, s in E3['expr'].items():
    ax.plot([p['n'] for p in s], [p['sec'] * 1e3 for p in s], '-', marker=MK[m], color=C[m], lw=1.6, ms=5, label=m,
            ls='--' if 'функц' in m else '-')
ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlabel('Длина входа, лексем'); ax.set_ylabel('Время разбора, мс')
ax.set_title('а) язык выражений', fontsize=9); ax.legend(fontsize=7)
ax = axs[1]
langs = [('expr', 'выражения'), ('json', 'JSON'), ('pl0', 'PL/0')]
mm = ['LL(1)', 'SLR(1)', 'LALR(1)', 'LR(1)', 'ОП (матрица)', 'ОП (функции)']
w = 0.13
for i, m in enumerate(mm):
    ys = []
    for L, _ in langs:
        s = E3[L].get(m)
        ys.append(st.median(p['us_per_tok'] for p in s) if s else 0)
    ax.bar(np.arange(3) + (i - 2.5) * w, ys, w * 0.92, color=C[m], hatch=HATCH[m], edgecolor='white', lw=0.4, label=m)
ax.set_xticks(range(3), [l for _, l in langs]); ax.set_ylabel('мкс на лексему'); ax.set_title('б) удельное время (медиана)', fontsize=9)
save('fig6_speed')

# ---- Рис.7 диагностика ошибок
E4 = R['E4']
fig, axs = plt.subplots(1, 2, figsize=(7.2, 4.0), gridspec_kw={'width_ratios': [1.5, 1]})
ax = axs[0]
gs = ['G1', 'G3', 'G5', 'G6', 'G7']
mm = ['LL(1)', 'SLR(1)', 'LALR(1)', 'LALR(1)+DR', 'LR(1)', 'ОП (матрица)', 'ОП (функции)']
w = 0.115
for i, m in enumerate(mm):
    ys = [100 * E4[g][m]['share_ideal'] if m in E4[g] else 0 for g in gs]
    ax.bar(np.arange(len(gs)) + (i - 3) * w, ys, w * 0.92, color=C[m], hatch=HATCH[m], edgecolor='white', lw=0.4, label=m)
ax.set_xticks(range(len(gs)), gs); ax.set_ylim(0, 105); ax.set_ylabel('Немедленное обнаружение, %')
ax.set_title('а) доля ошибок, найденных без задержки', fontsize=9)
fig.legend(*ax.get_legend_handles_labels(), fontsize=7.5, ncol=4, loc='lower center')
ax = axs[1]
fa = E4['synthB_OP']
vm = [100 * x['fa_matrix'] for x in fa]
vf = [100 * x['fa_funcs'] for x in fa if x['fa_funcs'] is not None]
binsh = [0, 0.001, 2, 5, 10, 20, 100]
lab = ['0', '(0;2]', '(2;5]', '(5;10]', '(10;20]', '>20']
hm = np.histogram(vm, bins=binsh)[0] / len(vm) * 100
hf = np.histogram(vf, bins=binsh)[0] / len(vf) * 100
ax.bar(np.arange(6) - 0.2, hm, 0.38, color=C['ОП (матрица)'], label='матрица', edgecolor='white')
ax.bar(np.arange(6) + 0.2, hf, 0.38, color=C['ОП (функции)'], hatch='--', label='функции', edgecolor='white')
ax.set_xticks(range(6), lab, fontsize=7.5, rotation=30); ax.set_xlabel('Ложно допущено цепочек, %')
ax.set_ylabel('Доля грамматик, %'); ax.set_title('б) ложные допуски ОП (корпус B)', fontsize=9); ax.legend(fontsize=7.5)
plt.tight_layout(rect=(0, 0.1, 1, 1)); plt.savefig('fig/fig7_errors.png', facecolor='white'); plt.close()

# ---- Рис.8 интегральный профиль
methods = ['LL(1)', 'SLR(1)', 'LALR(1)', 'LR(1)', 'ОП (матрица)']
power = {'LL(1)': st.mean(a['LL'] for a in A), 'SLR(1)': st.mean(a['SLR'] for a in A), 'LALR(1)': st.mean(a['LALR'] for a in A),
         'LR(1)': st.mean(a['LR1'] for a in A), 'ОП (матрица)': st.mean(a['OP'] for a in A)}
r10 = [r for r in E5 if r['k'] == 10][0]
size = {'LL(1)': r10['cells_ll'], 'SLR(1)': r10['cells_lalr'], 'LALR(1)': r10['cells_lalr'], 'LR(1)': r10['cells_lr1'], 'ОП (матрица)': r10['cells_op']}
speed = {m: st.median(p['us_per_tok'] for p in E3['json'][m]) for m in methods}
diag = {m: st.mean(E4[g][m]['share_ideal'] for g in ['G1', 'G5'] if m in E4[g]) for m in methods}
r40 = [r for r in E5 if r['k'] == 40][0]
build = {'LL(1)': r40['t_ll'], 'SLR(1)': r40['t_slr'], 'LALR(1)': r40['t_lalr'], 'LR(1)': r40['t_lr1'], 'ОП (матрица)': r40['t_op']}
crit = [('Распознающая\nмощность', {m: power[m] / max(power.values()) for m in methods}),
        ('Компактность\nтаблиц', {m: min(size.values()) / size[m] for m in methods}),
        ('Скорость\nразбора', {m: min(speed.values()) / speed[m] for m in methods}),
        ('Качество\nдиагностики', {m: diag[m] for m in methods}),
        ('Дешевизна\nпостроения', {m: math.log10(max(build.values()) / build[m] * 10) / math.log10(max(build.values()) / min(build.values()) * 10) for m in methods})]
ang = np.linspace(0, 2 * np.pi, len(crit), endpoint=False).tolist(); ang += ang[:1]
fig = plt.figure(figsize=(7.4, 4.6)); ax = fig.add_axes([0.06, 0.1, 0.5, 0.8], polar=True)
integral = {}
for m in methods:
    v = [c[1][m] for c in crit]; integral[m] = st.mean(v); v += v[:1]
    ax.plot(ang, v, '-', marker=MK[m], color=C[m], lw=1.8, ms=5, label=f'{m}: I = {integral[m]:.2f}')
    ax.fill(ang, v, color=C[m], alpha=0.06)
ax.set_xticks(ang[:-1], [c[0] for c in crit], fontsize=8.5); ax.tick_params(axis='x', pad=14); ax.set_ylim(0, 1.05); ax.set_yticks([0.25, 0.5, 0.75, 1.0], ['0.25', '0.5', '0.75', '1'], fontsize=7)
ax.legend(loc='center left', bbox_to_anchor=(1.18, 0.5), fontsize=8.5)
plt.savefig('fig/fig8_radar.png', facecolor='white'); plt.close()
json.dump({'crit': {c[0].replace('\n', ' '): c[1] for c in crit}, 'integral': integral, 'raw': {'power': power, 'size': size, 'speed': speed, 'diag': diag, 'build': build}},
          open('integral.json', 'w'), ensure_ascii=False, indent=1)
print(integral)

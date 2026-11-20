"""Эксперименты E1–E4. Результаты сохраняются в results.json."""
import json, math, random, statistics, time, sys
from collections import defaultdict, Counter
from parsing_lab import *
from parsing_lab import _augment
from grammars import load, GRAMMARS

R = {}
G = load()


def build_all(g):
    ga = _augment(g)[0]
    t0 = time.perf_counter(); ll = LL1(g); t_ll = time.perf_counter() - t0
    t0 = time.perf_counter(); slr = SLR1(g); t_slr = time.perf_counter() - t0
    t0 = time.perf_counter(); A = LR1Automaton(ga); lr = LR1(g, A); t_lr = time.perf_counter() - t0
    la = LALR1(g, A)
    op = OperatorPrecedence(g)
    return dict(LL=ll, SLR=slr, LALR=la, LR1=lr, OP=op), dict(LL=t_ll, SLR=t_slr, LR1=t_lr)


def timeit(f, rep=7):
    xs = []
    for _ in range(rep):
        t0 = time.perf_counter(); f(); xs.append(time.perf_counter() - t0)
    return statistics.median(xs)


# ------------------------------------------------------------- E1 таблицы
print('E1', file=sys.stderr)
e1 = {}
for k, g in G.items():
    P, _ = build_all(g)
    ga = _augment(g)[0]
    t_ll = timeit(lambda: LL1(g))
    t_slr = timeit(lambda: SLR1(g))
    t_lalr = timeit(lambda: LALR1Prop(g))
    t_lr = timeit(lambda: LR1(g, LR1Automaton(ga)))
    t_op = timeit(lambda: OperatorPrecedence(g)) if P['OP'].operator_form else None
    lldr = P['LALR'].with_default_reductions()
    gll = to_ll(g) if P['LL'].conflicts else g
    ll2 = LL1(gll) if gll else None
    row = {'name': GRAMMARS[k][0], 'size': g.size(),
           'LL': P['LL'].stats(), 'SLR': P['SLR'].stats(), 'LALR': P['LALR'].stats(),
           'LR1': P['LR1'].stats(), 'LALR_DR_filled': lldr.filled_compressed,
           'LL_transformed': ({'size': gll.size(), **ll2.stats()} if (gll is not g and gll) else None),
           'OP_form': P['OP'].operator_form,
           'OP': P['OP'].stats() if P['OP'].operator_form else None,
           'OP_funcs': (P['OP'].funcs is not None) if P['OP'].operator_form and P['OP'].conflicts == 0 else None,
           'time_ms': {'LL': t_ll * 1e3, 'SLR': t_slr * 1e3, 'LALR': t_lalr * 1e3, 'LR1': t_lr * 1e3,
                       'OP': t_op * 1e3 if t_op else None}}
    if P['OP'].funcs:
        f, gg = P['OP'].funcs
        row['OP_funcs_vals'] = {'f': f, 'g': gg}
    e1[k] = row
R['E1'] = e1

# ------------------------------------------------------------- E2 синтетический корпус
print('E2', file=sys.stderr)
def classify(g, with_transform=True):
    ga = _augment(g)[0]
    res = {}
    res['LL'] = LL1(g).conflicts == 0
    res['SLR'] = SLR1(g).conflicts == 0
    try:
        A = LR1Automaton(ga, limit=20000)
    except RuntimeError:
        return None
    lr = LR1(g, A); la = LALR1(g, A)
    res['LALR'] = la.conflicts == 0
    res['LR1'] = lr.conflicts == 0
    op = OperatorPrecedence(g)
    res['OPform'] = op.operator_form
    res['OP'] = bool(op.operator_form and op.conflicts == 0)
    res['OPfun'] = bool(res['OP'] and op.funcs is not None)
    res['n0'] = la.nstates; res['n1'] = lr.nstates
    if with_transform:
        if res['LL']:
            res['LLt'] = True; res['growth'] = 1.0
        else:
            t = to_ll(g)
            res['LLt'] = bool(t and LL1(t).conflicts == 0)
            res['growth'] = (t.size()['|G|'] / g.size()['|G|']) if t else None
    return res


def corpus(seed, count, operator):
    rng = random.Random(seed)
    out = []
    while len(out) < count:
        n_nt = rng.randint(2, 10); n_t = rng.randint(2, 8)
        g = random_grammar(rng, n_nt, n_t, operator=operator)
        if g is None:
            continue
        c = classify(g)
        if c is None:
            continue
        c['N'] = len(g.nonterms); c['P'] = len(g.prods); c['G'] = g.size()['|G|']
        out.append(c)
    return out

A = corpus(2026, 3000, operator=False)
B = corpus(7, 2000, operator=True)
R['E2'] = {'A': A, 'B': B}

# ------------------------------------------------------------- E3 скорость
print('E3', file=sys.stderr)
e3 = {}
def speed_series(lang_gen_grammar, parsers, lengths, seed=5):
    rng = random.Random(seed)
    h = heights(lang_gen_grammar)
    res = defaultdict(list)
    for n in lengths:
        s = generate(lang_gen_grammar, n, rng, h)
        while len(s) < 0.9 * n:
            s = generate(lang_gen_grammar, n, rng, h)
        for name, p in parsers.items():
            ok = p.parse(s)[0]
            assert ok, (name, n)
            p.parse(s)
            t = min(timeit(lambda: p.parse(s), rep=1) for _ in range(9))
            res[name].append({'n': len(s), 'us_per_tok': t / len(s) * 1e6, 'sec': t})
    return dict(res)

g1, g2 = G['G1'], G['G2']
P1, _ = build_all(g1)
expr_parsers = {'LL(1)': LL1(g2), 'SLR(1)': P1['SLR'], 'LALR(1)': P1['LALR'], 'LR(1)': P1['LR1'],
                'ОП (матрица)': OperatorPrecedence(g1), 'ОП (функции)': OperatorPrecedence(g1, True)}
e3['expr'] = speed_series(g1, expr_parsers, [1000, 2000, 4000, 8000, 16000, 32000, 64000])
P6, _ = build_all(G['G6'])
e3['pl0'] = speed_series(G['G6'], {'LL(1)': P6['LL'], 'SLR(1)': P6['SLR'], 'LALR(1)': P6['LALR'], 'LR(1)': P6['LR1']},
                         [1000, 4000, 16000, 64000])
P5, _ = build_all(G['G5'])
g5ll = to_ll(G['G5'])
e3['json'] = speed_series(G['G5'], {'LL(1)': LL1(g5ll), 'SLR(1)': P5['SLR'], 'LALR(1)': P5['LALR'], 'LR(1)': P5['LR1'],
                                   'ОП (матрица)': OperatorPrecedence(G['G5']), 'ОП (функции)': OperatorPrecedence(G['G5'], True)},
                         [1000, 4000, 16000, 64000])
# шаги разбора на токен
steps = {}
rng = random.Random(9)
s = generate(g1, 20000, rng)
for name, p in expr_parsers.items():
    steps[name] = p.parse(s)[3] / len(s)
e3['steps_per_token_expr'] = steps
R['E3'] = e3

# ------------------------------------------------------------- E4 ошибки
print('E4', file=sys.stderr)
def error_experiment(gen_g, truth, parsers, n=2000, seed=11, budget=25):
    rng = random.Random(seed)
    h = heights(gen_g)
    terms = gen_g.terms
    stats = {k: {'detected': 0, 'dpos': [], 'extra': [], 'false_accept': 0, 'ideal': 0} for k in parsers}
    count = 0; ops = Counter(); tries = 0
    while count < n and tries < n * 20:
        tries += 1
        s = generate(gen_g, rng.randint(3, budget), rng, h)
        m, op = mutate(s, terms, rng)
        ok, e, _, _ = truth.parse(m)
        if ok:
            continue
        count += 1; ops[op] += 1
        for k, p in parsers.items():
            pok, pos, extra, _ = p.parse(m)
            st = stats[k]
            if pok:
                st['false_accept'] += 1
            else:
                st['detected'] += 1
                st['dpos'].append(pos - e)
                st['extra'].append(extra)
                if pos == e and extra == 0:
                    st['ideal'] += 1
    out = {}
    for k, st in stats.items():
        d = st['dpos']; x = st['extra']
        out[k] = {'n': count, 'detect_rate': st['detected'] / count,
                  'false_accept_rate': st['false_accept'] / count,
                  'mean_dpos': statistics.mean(d) if d else None,
                  'share_late': sum(1 for v in d if v > 0) / len(d) if d else None,
                  'mean_extra': statistics.mean(x) if x else None,
                  'share_extra': sum(1 for v in x if v > 0) / len(x) if x else None,
                  'max_extra': max(x) if x else None,
                  'share_ideal': st['ideal'] / count,
                  'hist_extra': dict(Counter(min(v, 6) for v in x))}
    return out

e4 = {}
e4['G1'] = error_experiment(g1, P1['LR1'], {
    'LL(1)': LL1(g2), 'SLR(1)': P1['SLR'], 'LALR(1)': P1['LALR'], 'LALR(1)+DR': P1['LALR'].with_default_reductions(),
    'LR(1)': P1['LR1'], 'ОП (матрица)': OperatorPrecedence(g1), 'ОП (функции)': OperatorPrecedence(g1, True)})
P3, _ = build_all(G['G3'])
e4['G3'] = error_experiment(G['G3'], P3['LR1'], {
    'LALR(1)': P3['LALR'], 'LALR(1)+DR': P3['LALR'].with_default_reductions(), 'LR(1)': P3['LR1'],
    'ОП (матрица)': OperatorPrecedence(G['G3']), 'ОП (функции)': OperatorPrecedence(G['G3'], True)})
e4['G5'] = error_experiment(G['G5'], P5['LR1'], {
    'LL(1)': LL1(g5ll), 'SLR(1)': P5['SLR'], 'LALR(1)': P5['LALR'], 'LALR(1)+DR': P5['LALR'].with_default_reductions(),
    'LR(1)': P5['LR1'], 'ОП (матрица)': OperatorPrecedence(G['G5']), 'ОП (функции)': OperatorPrecedence(G['G5'], True)})
e4['G6'] = error_experiment(G['G6'], P6['LR1'], {
    'LL(1)': P6['LL'], 'SLR(1)': P6['SLR'], 'LALR(1)': P6['LALR'], 'LALR(1)+DR': P6['LALR'].with_default_reductions(),
    'LR(1)': P6['LR1']}, budget=40)
P7, _ = build_all(G['G7'])
e4['G7'] = error_experiment(G['G7'], P7['LR1'], {
    'SLR(1)': P7['SLR'], 'LALR(1)': P7['LALR'], 'LALR(1)+DR': P7['LALR'].with_default_reductions(),
    'LR(1)': P7['LR1']}, budget=40)

# ОП на синтетическом корпусе B: ложные допуски
rng = random.Random(77)
fa = []
cntg = 0
while cntg < 300:
    g = random_grammar(rng, rng.randint(2, 8), rng.randint(2, 6), operator=True)
    if g is None:
        continue
    op = OperatorPrecedence(g)
    if not (op.operator_form and op.conflicts == 0):
        continue
    try:
        lr = LR1(g, LR1Automaton(_augment(g)[0], limit=20000))
    except RuntimeError:
        continue
    if lr.conflicts:
        continue
    cntg += 1
    r = error_experiment(g, lr, {'ОП (матрица)': op} | ({'ОП (функции)': OperatorPrecedence(g, True)} if op.funcs else {}),
                         n=200, seed=cntg, budget=15)
    # проверка: правильные цепочки допускаются
    hh = heights(g); ok_valid = all(op.parse(generate(g, rng.randint(1, 15), rng, hh))[0] for _ in range(50))
    fa.append({'N': len(g.nonterms), 'P': len(g.prods), 'valid_ok': ok_valid,
               'fa_matrix': r['ОП (матрица)']['false_accept_rate'],
               'fa_funcs': r['ОП (функции)']['false_accept_rate'] if 'ОП (функции)' in r else None,
               'late_matrix': r['ОП (матрица)']['mean_dpos'],
               'late_funcs': r['ОП (функции)']['mean_dpos'] if 'ОП (функции)' in r else None})
e4['synthB_OP'] = fa
R['E4'] = e4

# ------------------------------------------------------------- E5 масштабирование по числу уровней приоритета
print('E5', file=sys.stderr)
def levels_grammar(k):
    lines = ['S -> S ; E0 | E0']
    for i in range(k):
        lines.append(f'E{i} -> E{i} o{i} E{i+1} | E{i+1}')
    lines.append(f'E{k} -> ( E0 ) | id')
    return Grammar.parse('\n'.join(lines), name=f'L{k}')
e5 = []
for k in [2, 4, 6, 8, 10, 14, 18, 24, 30, 40]:
    g = levels_grammar(k); ga = _augment(g)[0]
    row = {'k': k, 'P': len(g.prods), 'T': len(g.terms)}
    row['t_slr'] = min(timeit(lambda: SLR1(g), rep=1) for _ in range(3)) * 1e3
    row['t_lalr'] = min(timeit(lambda: LALR1Prop(g), rep=1) for _ in range(3)) * 1e3
    row['t_lr1'] = min(timeit(lambda: LR1(g, LR1Automaton(ga)), rep=1) for _ in range(3)) * 1e3
    row['t_op'] = min(timeit(lambda: OperatorPrecedence(g), rep=1) for _ in range(3)) * 1e3
    gl = to_ll(g); row['t_ll'] = min(timeit(lambda: LL1(gl), rep=1) for _ in range(3)) * 1e3
    lr = LR1(g); la = LALR1Prop(g); op = OperatorPrecedence(g); ll = LL1(gl)
    row.update({'n0': la.nstates, 'n1': lr.nstates, 'lalr_conf': la.conflicts, 'lr_conf': lr.conflicts,
                'll_conf': ll.conflicts, 'op_conf': op.conflicts, 'op_funcs': op.funcs is not None,
                'cells_ll': ll.stats()['filled'], 'cells_lalr': la.stats()['filled'],
                'cells_lalr_dr': la.with_default_reductions().filled_compressed,
                'cells_lr1': lr.stats()['filled'], 'cells_op': op.stats()['filled'], 'cells_opf': 2 * (len(g.terms) + 1)})
    e5.append(row)
R['E5'] = e5

json.dump(R, open('results.json', 'w'), ensure_ascii=False, indent=1, default=str)
print('done', file=sys.stderr)

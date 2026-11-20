"""
parsing_lab.py — единая реализация табличных методов синтаксического разбора
для сравнительного эксперимента: LL(1), SLR(1), LALR(1), каноническое LR(1)
и операторное предшествование Флойда (матрица отношений и функции предшествования).

Все методы используют одно представление грамматики и единый формат
трассировки, что позволяет сравнивать их на одинаковых входных данных.
"""
from __future__ import annotations
from collections import defaultdict, deque
import random

EPS = ()          # пустая правая часть
END = '$'         # маркер конца входа


# ---------------------------------------------------------------- грамматика
class Grammar:
    def __init__(self, prods, start=None, name=''):
        """prods: список (A, tuple(rhs)); первый нетерминал — аксиома."""
        self.name = name
        self.prods = [(a, tuple(r)) for a, r in prods]
        self.start = start or self.prods[0][0]
        self.nonterms = []
        for a, _ in self.prods:
            if a not in self.nonterms:
                self.nonterms.append(a)
        ns = set(self.nonterms)
        terms = []
        for _, r in self.prods:
            for s in r:
                if s not in ns and s not in terms:
                    terms.append(s)
        self.terms = terms
        self.by_lhs = defaultdict(list)
        for i, (a, r) in enumerate(self.prods):
            self.by_lhs[a].append(i)
        self._first()
        self._follow()

    @staticmethod
    def parse(text, name=''):
        """Формат: 'A -> x B | y | eps' по строке на нетерминал."""
        prods = []
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            lhs, rhs = line.split('->')
            for alt in rhs.split(' | '):
                syms = alt.split()
                prods.append((lhs.strip(), tuple() if syms in (['eps'], []) else tuple(syms)))
        return Grammar(prods, name=name)

    def is_nt(self, s):
        return s in self.by_lhs

    # FIRST / FOLLOW
    def _first(self):
        self.nullable = set()
        self.FIRST = {a: set() for a in self.nonterms}
        changed = True
        while changed:
            changed = False
            for a, r in self.prods:
                f, nul = self.first_seq_raw(r)
                if not f <= self.FIRST[a]:
                    self.FIRST[a] |= f; changed = True
                if nul and a not in self.nullable:
                    self.nullable.add(a); changed = True

    def first_seq_raw(self, seq):
        out = set()
        for s in seq:
            if not self.is_nt(s):
                out.add(s); return out, False
            out |= self.FIRST[s]
            if s not in self.nullable:
                return out, False
        return out, True

    def first_seq(self, seq):
        return self.first_seq_raw(seq)

    def _follow(self):
        self.FOLLOW = {a: set() for a in self.nonterms}
        self.FOLLOW[self.start].add(END)
        changed = True
        while changed:
            changed = False
            for a, r in self.prods:
                for i, s in enumerate(r):
                    if not self.is_nt(s):
                        continue
                    f, nul = self.first_seq(r[i + 1:])
                    add = f | (self.FOLLOW[a] if nul else set())
                    if not add <= self.FOLLOW[s]:
                        self.FOLLOW[s] |= add; changed = True

    def size(self):
        return {'N': len(self.nonterms), 'T': len(self.terms), 'P': len(self.prods),
                '|G|': sum(len(r) + 1 for _, r in self.prods)}

    def text(self):
        lines = []
        for a in self.nonterms:
            alts = [' '.join(self.prods[i][1]) or 'ε' for i in self.by_lhs[a]]
            lines.append(f"{a} → " + ' | '.join(alts))
        return lines


# ---------------------------------------------------------------- LL(1)
class LL1:
    method = 'LL(1)'

    def __init__(self, g: Grammar):
        self.g = g
        cells = defaultdict(list)
        for i, (a, r) in enumerate(g.prods):
            f, nul = g.first_seq(r)
            la = f | (g.FOLLOW[a] if nul else set())
            for t in la:
                if i not in cells[(a, t)]:
                    cells[(a, t)].append(i)
        self.cells = cells
        self.conflicts = sum(1 for v in cells.values() if len(v) > 1)
        self.table = {k: v[0] for k, v in cells.items()}

    def stats(self):
        return {'rows': len(self.g.nonterms), 'cols': len(self.g.terms) + 1,
                'cells': len(self.g.nonterms) * (len(self.g.terms) + 1),
                'filled': len(self.cells), 'conflicts': self.conflicts}

    def parse(self, tokens, trace=False):
        """Возвращает (ok, pos_ошибки, лишние_шаги_на_ошибочном_символе, всего_шагов)."""
        g, M = self.g, self.table
        toks = list(tokens) + [END]
        stack = [END, g.start]
        i = 0; steps = 0; since_shift = 0
        isnt = g.by_lhs.__contains__
        prods = g.prods
        while True:
            top = stack.pop()
            a = toks[i]
            if top == END:
                return (a == END), i, since_shift, steps
            if not isnt(top):
                if top == a:
                    i += 1; since_shift = 0; steps += 1
                    continue
                return False, i, since_shift, steps
            p = M.get((top, a))
            if p is None:
                return False, i, since_shift, steps
            rhs = prods[p][1]
            stack.extend(reversed(rhs))
            steps += 1; since_shift += 1


# ---------------------------------------------------------------- LR-автоматы
class LRBase:
    """Общий драйвер LR-разбора по таблицам ACTION/GOTO."""
    method = 'LR'

    def _finish(self, action_lists):
        self.action_lists = action_lists
        self.conflicts = 0; self.sr = 0; self.rr = 0
        action = {}
        for (s, t), acts in action_lists.items():
            acts = list(dict.fromkeys(acts))
            if len(acts) > 1:
                self.conflicts += 1
                kinds = {k for k, _ in acts}
                if 's' in kinds:
                    self.sr += 1
                else:
                    self.rr += 1
                # разрешение как в yacc: сдвиг, иначе правило с меньшим номером
                sh = [x for x in acts if x[0] == 's']
                acts = sh if sh else sorted(acts, key=lambda x: x[1])
            action[(s, t)] = acts[0]
        self.action = action

    def stats(self):
        T = len(self.g.terms) + 1; N = len(self.g.nonterms)
        return {'states': self.nstates, 'cells': self.nstates * (T + N),
                'filled': len(self.action) + len(self.goto),
                'conflicts': self.conflicts, 'sr': self.sr, 'rr': self.rr}

    def with_default_reductions(self):
        """Сжатие в стиле yacc/bison: самая частая свёртка состояния становится
        действием по умолчанию для всех пустых клеток строки."""
        clone = object.__new__(type(self))
        clone.__dict__.update(self.__dict__)
        rows = defaultdict(dict)
        for (s, t), act in self.action.items():
            rows[s][t] = act
        default = {}
        filled_after = 0
        for s, row in rows.items():
            red = [a for a in row.values() if a[0] == 'r']
            if red:
                cnt = defaultdict(int)
                for a in red:
                    cnt[a] += 1
                d = max(cnt, key=cnt.get)
                default[s] = d
                filled_after += sum(1 for a in row.values() if a != d) + 1
            else:
                filled_after += len(row)
        clone.default = default
        clone.method = self.method + '+DR'
        clone.filled_compressed = filled_after + len(self.goto)
        return clone

    def parse(self, tokens, trace=False):
        toks = list(tokens) + [END]
        action, goto, prods = self.action, self.goto, self.g.prods
        default = getattr(self, 'default', None)
        stack = [0]
        i = 0; steps = 0; since_shift = 0
        while True:
            s = stack[-1]; a = toks[i]
            act = action.get((s, a))
            if act is None and default is not None:
                act = default.get(s)
            if act is None:
                return False, i, since_shift, steps
            k = act[0]
            if k == 's':
                stack.append(act[1]); i += 1; since_shift = 0
            elif k == 'r':
                lhs, rhs = prods[act[1]]
                if rhs:
                    del stack[-len(rhs):]
                nxt = goto.get((stack[-1], lhs))
                if nxt is None:            # возможно только при сжатых таблицах
                    return False, i, since_shift, steps
                stack.append(nxt); since_shift += 1
            else:
                return True, i, since_shift, steps
            steps += 1


def _augment(g: Grammar):
    S0 = g.start + "'"
    while S0 in g.by_lhs:
        S0 += "'"
    return Grammar([(S0, (g.start,))] + g.prods, name=g.name), S0


class LR0Automaton:
    def __init__(self, ga: Grammar):
        self.ga = ga
        g = ga
        def closure(items):
            res = set(items); work = list(items)
            while work:
                p, d = work.pop()
                r = g.prods[p][1]
                if d < len(r) and g.is_nt(r[d]):
                    for q in g.by_lhs[r[d]]:
                        if (q, 0) not in res:
                            res.add((q, 0)); work.append((q, 0))
            return frozenset(res)
        k0 = frozenset([(0, 0)])
        self.kernels = [k0]; self.closures = [closure(k0)]
        idx = {k0: 0}; self.trans = {}
        q = deque([0])
        while q:
            s = q.popleft()
            moves = defaultdict(set)
            for p, d in self.closures[s]:
                r = g.prods[p][1]
                if d < len(r):
                    moves[r[d]].add((p, d + 1))
            for X, ker in moves.items():
                ker = frozenset(ker)
                if ker not in idx:
                    idx[ker] = len(self.kernels)
                    self.kernels.append(ker); self.closures.append(closure(ker))
                    q.append(idx[ker])
                self.trans[(s, X)] = idx[ker]


class SLR1(LRBase):
    method = 'SLR(1)'

    def __init__(self, g: Grammar, lr0: LR0Automaton | None = None):
        self.g = g
        ga, _ = _augment(g)
        self.ga = ga
        A = lr0 or LR0Automaton(ga)
        self.nstates = len(A.kernels)
        acts = defaultdict(list); self.goto = {}
        for (s, X), t in A.trans.items():
            if ga.is_nt(X):
                self.goto[(s, X)] = t
            else:
                acts[(s, X)].append(('s', t))
        for s, items in enumerate(A.closures):
            for p, d in items:
                lhs, r = ga.prods[p]
                if d == len(r):
                    if p == 0:
                        acts[(s, END)].append(('acc', 0))
                    else:
                        for t in ga.FOLLOW[lhs]:
                            acts[(s, t)].append(('r', p - 1))
        # индексы правил сдвинуты на 1 из-за пополнения
        self._finish(acts)


class LR1Automaton:
    """Каноническая совокупность LR(1)-ситуаций (Кнут)."""
    def __init__(self, ga: Grammar, limit=200000):
        g = ga
        suf_cache = {}
        def suffix_first(p, d):
            key = (p, d)
            if key not in suf_cache:
                suf_cache[key] = g.first_seq(g.prods[p][1][d:])
            return suf_cache[key]
        def closure(kernel):
            la = defaultdict(set)
            for p, d, a in kernel:
                la[(p, d)].add(a)
            work = deque(la.keys())
            while work:
                p, d = work.popleft()
                r = g.prods[p][1]
                if d < len(r) and g.is_nt(r[d]):
                    f, nul = suffix_first(p, d + 1)
                    new = set(f)
                    if nul:
                        new |= la[(p, d)]
                    for q in g.by_lhs[r[d]]:
                        cur = la[(q, 0)]
                        if not new <= cur:
                            cur |= new
                            work.append((q, 0))
            return la
        k0 = frozenset([(0, 0, END)])
        self.kernels = [k0]; self.closures = [closure(k0)]
        idx = {k0: 0}; self.trans = {}
        q = deque([0])
        while q:
            s = q.popleft()
            moves = defaultdict(set)
            for (p, d), las in self.closures[s].items():
                r = g.prods[p][1]
                if d < len(r):
                    for a in las:
                        moves[r[d]].add((p, d + 1, a))
            for X, ker in moves.items():
                ker = frozenset(ker)
                if ker not in idx:
                    idx[ker] = len(self.kernels)
                    if idx[ker] > limit:
                        raise RuntimeError('LR(1): превышен предел числа состояний')
                    self.kernels.append(ker); self.closures.append(closure(ker))
                    q.append(idx[ker])
                self.trans[(s, X)] = idx[ker]


class LR1(LRBase):
    method = 'LR(1)'

    def __init__(self, g: Grammar, auto: LR1Automaton | None = None):
        self.g = g
        ga, _ = _augment(g); self.ga = ga
        A = auto or LR1Automaton(ga)
        self.auto = A
        self.nstates = len(A.kernels)
        acts = defaultdict(list); self.goto = {}
        for (s, X), t in A.trans.items():
            if ga.is_nt(X):
                self.goto[(s, X)] = t
            else:
                acts[(s, X)].append(('s', t))
        for s, cl in enumerate(A.closures):
            for (p, d), las in cl.items():
                if d == len(ga.prods[p][1]):
                    for a in las:
                        acts[(s, a)].append(('acc', 0) if p == 0 else ('r', p - 1))
        self._finish(acts)


class LALR1(LRBase):
    """LALR(1) — слияние состояний канонического LR(1)-автомата с одинаковым ядром."""
    method = 'LALR(1)'

    def __init__(self, g: Grammar, auto: LR1Automaton | None = None):
        self.g = g
        ga, _ = _augment(g); self.ga = ga
        A = auto or LR1Automaton(ga)
        core_id = {}; m = []
        for k in A.kernels:
            c = frozenset((p, d) for p, d, _ in k)
            if c not in core_id:
                core_id[c] = len(core_id)
            m.append(core_id[c])
        self.nstates = len(core_id)
        acts = defaultdict(list); self.goto = {}
        for (s, X), t in A.trans.items():
            if ga.is_nt(X):
                self.goto[(m[s], X)] = m[t]
            else:
                if ('s', m[t]) not in acts[(m[s], X)]:
                    acts[(m[s], X)].append(('s', m[t]))
        for s, cl in enumerate(A.closures):
            for (p, d), las in cl.items():
                if d == len(ga.prods[p][1]):
                    for a in las:
                        act = ('acc', 0) if p == 0 else ('r', p - 1)
                        if act not in acts[(m[s], a)]:
                            acts[(m[s], a)].append(act)
        self._finish(acts)


# ---------------------------------------------------------------- предшествование
LT, EQ, GT = '<', '=', '>'


class OperatorPrecedence:
    """Операторное предшествование Флойда.
    use_functions=True — разбор по функциям предшествования f, g (сжатое представление)."""
    method = 'ОП'

    def __init__(self, g: Grammar, use_functions=False):
        self.g = g
        self.operator_form = all(len(r) > 0 for _, r in g.prods) and not any(
            g.is_nt(r[i]) and g.is_nt(r[i + 1]) for _, r in g.prods for i in range(len(r) - 1))
        self.use_functions = use_functions
        self.method = 'ОП (функции)' if use_functions else 'ОП (матрица)'
        self.funcs = None
        if not self.operator_form:
            self.conflicts = None
            return
        # LEADING / TRAILING
        lead = {a: set() for a in g.nonterms}; trail = {a: set() for a in g.nonterms}
        changed = True
        while changed:
            changed = False
            for a, r in g.prods:
                # leading
                new = set()
                if not g.is_nt(r[0]):
                    new.add(r[0])
                else:
                    new |= lead[r[0]]
                    if len(r) > 1:
                        new.add(r[1])
                if not new <= lead[a]:
                    lead[a] |= new; changed = True
                new = set()
                if not g.is_nt(r[-1]):
                    new.add(r[-1])
                else:
                    new |= trail[r[-1]]
                    if len(r) > 1:
                        new.add(r[-2])
                if not new <= trail[a]:
                    trail[a] |= new; changed = True
        rel = defaultdict(set)
        for _, r in g.prods:
            for i in range(len(r) - 1):
                x, y = r[i], r[i + 1]
                if not g.is_nt(x) and not g.is_nt(y):
                    rel[(x, y)].add(EQ)
                if i + 2 < len(r) and not g.is_nt(x) and g.is_nt(y) and not g.is_nt(r[i + 2]):
                    rel[(x, r[i + 2])].add(EQ)
                if not g.is_nt(x) and g.is_nt(y):
                    for b in lead[y]:
                        rel[(x, b)].add(LT)
                if g.is_nt(x) and not g.is_nt(y):
                    for a in trail[x]:
                        rel[(a, y)].add(GT)
        for b in lead[g.start]:
            rel[(END, b)].add(LT)
        for a in trail[g.start]:
            rel[(a, END)].add(GT)
        self.rel = rel
        self.conflicts = sum(1 for v in rel.values() if len(v) > 1)
        self.R = {k: next(iter(v)) for k, v in rel.items() if len(v) == 1}
        # скелеты правых частей: нетерминалы обезличены
        self.skeletons = {tuple('N' if g.is_nt(s) else s for s in r) for _, r in g.prods}
        self.funcs = self._functions() if self.conflicts == 0 else None

    def _functions(self):
        """Функции предшествования f, g: построение по графу (метод Белла)."""
        T = self.g.terms + [END]
        parent = {}
        def find(x):
            while parent.setdefault(x, x) != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        for (a, b), r in self.R.items():
            if r == EQ:
                parent[find(('f', a))] = find(('g', b))
        nodes = {find(('f', a)) for a in T} | {find(('g', a)) for a in T}
        edges = defaultdict(set)
        for (a, b), r in self.R.items():
            if r == GT:
                edges[find(('f', a))].add(find(('g', b)))
            elif r == LT:
                edges[find(('g', b))].add(find(('f', a)))
        memo = {}; onstack = set()
        def longest(n):
            if n in memo:
                return memo[n]
            if n in onstack:
                raise ValueError('cycle')
            onstack.add(n)
            v = 0
            for m in edges[n]:
                v = max(v, 1 + longest(m))
            onstack.discard(n); memo[n] = v
            return v
        try:
            f = {a: longest(find(('f', a))) for a in T}
            gg = {a: longest(find(('g', a))) for a in T}
        except (ValueError, RecursionError):
            return None
        return f, gg

    def stats(self):
        T = len(self.g.terms) + 1
        if self.use_functions:
            return {'cells': 2 * T, 'filled': 2 * T if self.funcs else None, 'conflicts': self.conflicts}
        return {'cells': T * T, 'filled': len(self.R), 'conflicts': self.conflicts}

    def relation(self, a, b):
        if self.use_functions:
            f, g = self.funcs
            if a not in f or b not in g:
                return None
            x, y = f[a], g[b]
            return LT if x < y else (GT if x > y else EQ)
        return self.R.get((a, b))

    def parse(self, tokens, trace=False):
        toks = list(tokens) + [END]
        stack = [END]                     # терминалы и обезличенный 'N'
        i = 0; steps = 0; since_shift = 0
        rel = self.relation; isN = 'N'.__eq__
        while True:
            a = toks[i]
            j = len(stack) - 1
            while isN(stack[j]):
                j -= 1
            top = stack[j]
            if top == END and a == END:
                return stack == [END, 'N'], i, since_shift, steps
            r = rel(top, a)
            if r is None:
                return False, i, since_shift, steps
            if r != GT:
                if a == END:
                    return False, i, since_shift, steps
                stack.append(a); i += 1; since_shift = 0; steps += 1
                continue
            # свёртка: ищем левую границу основы
            k = j
            while True:
                last = stack[k]
                k -= 1
                while isN(stack[k]):
                    k -= 1
                rk = rel(stack[k], last)
                if rk == LT:
                    break
                if rk != EQ or k == 0:
                    return False, i, since_shift, steps
            handle = tuple(stack[k + 1:])
            if handle not in self.skeletons:
                return False, i, since_shift, steps
            del stack[k + 1:]
            stack.append('N')
            steps += 1; since_shift += 1


# ---------------------------------------------------------------- генерация цепочек
def heights(g: Grammar):
    h = {a: float('inf') for a in g.nonterms}
    changed = True
    while changed:
        changed = False
        for a, r in g.prods:
            v = 1 + max([h[s] for s in r if g.is_nt(s)] or [0])
            if v < h[a]:
                h[a] = v; changed = True
    return h


def generate(g: Grammar, budget: int, rng: random.Random, h=None):
    """Случайная левосторонняя порождающая цепочка длиной около budget."""
    h = h or heights(g)
    ph = {i: 1 + max([h[s] for s in r if g.is_nt(s)] or [0]) for i, (_, r) in enumerate(g.prods)}
    out = []; stack = [g.start]
    pending = 1
    while stack:
        s = stack.pop()
        if not g.is_nt(s):
            out.append(s); pending -= 1; continue
        pending -= 1
        opts = g.by_lhs[s]
        if len(out) + pending < budget:
            rec = [q for q in opts if any(g.is_nt(x) for x in g.prods[q][1])]
            p = rng.choice(rec if rec and rng.random() < 0.85 else opts)
        else:
            best = min(ph[q] for q in opts)
            p = rng.choice([q for q in opts if ph[q] == best])
        r = g.prods[p][1]
        stack.extend(reversed(r)); pending += len(r)
    return out


def mutate(tokens, terms, rng: random.Random):
    t = list(tokens); op = rng.choice(['del', 'ins', 'rep', 'swap'])
    if op == 'del' and t:
        del t[rng.randrange(len(t))]
    elif op == 'ins':
        t.insert(rng.randrange(len(t) + 1), rng.choice(terms))
    elif op == 'rep' and t:
        t[rng.randrange(len(t))] = rng.choice(terms)
    elif len(t) > 1:
        k = rng.randrange(len(t) - 1); t[k], t[k + 1] = t[k + 1], t[k]
    return t, op


# ---------------------------------------------------------------- преобразования к LL(1)
def to_ll(g: Grammar, cap=300):
    """Устранение левой рекурсии (алгоритм Пола) и левая факторизация.
    Возвращает Grammar либо None, если рост превысил cap правил."""
    P = {a: [g.prods[i][1] for i in g.by_lhs[a]] for a in g.nonterms}
    order = list(g.nonterms)
    names = set(order) | set(g.terms)
    def fresh(a):
        n = a + "'"
        while n in names:
            n += "'"
        names.add(n); return n
    def total():
        return sum(len(v) for v in P.values())
    newnt = []
    for i, Ai in enumerate(order):
        for Aj in order[:i]:
            new = []
            for r in P[Ai]:
                if r and r[0] == Aj:
                    new.extend(gr + r[1:] for gr in P[Aj])
                else:
                    new.append(r)
            P[Ai] = list(dict.fromkeys(new))
            if total() > cap:
                return None
        alpha = [r[1:] for r in P[Ai] if r and r[0] == Ai and len(r) > 1]
        beta = [r for r in P[Ai] if not (r and r[0] == Ai)]
        if alpha:
            if not beta:
                return None
            A2 = fresh(Ai); newnt.append(A2)
            P[Ai] = [b + (A2,) for b in beta]
            P[A2] = [a + (A2,) for a in alpha] + [()]
        else:
            P[Ai] = beta if len(beta) < len(P[Ai]) else P[Ai]
    order += newnt
    # левая факторизация
    changed = True
    while changed:
        changed = False
        for A in list(P.keys()):
            groups = defaultdict(list)
            for r in P[A]:
                if r:
                    groups[r[0]].append(r)
            for x, grp in groups.items():
                if len(grp) < 2:
                    continue
                pre = grp[0]
                for r in grp[1:]:
                    k = 0
                    while k < min(len(pre), len(r)) and pre[k] == r[k]:
                        k += 1
                    pre = pre[:k]
                A2 = fresh(A); order.append(A2)
                P[A2] = list(dict.fromkeys(r[len(pre):] for r in grp))
                P[A] = [r for r in P[A] if r not in grp] + [pre + (A2,)]
                changed = True
                break
            if total() > cap:
                return None
    prods = [(a, r) for a in order for r in P.get(a, [])]
    try:
        return Grammar(prods, start=g.start, name=g.name + '-LL')
    except Exception:
        return None


# ---------------------------------------------------------------- случайные грамматики
def random_grammar(rng: random.Random, n_nt, n_t, operator=False, eps_prob=0.15):
    NT = [f'A{i}' for i in range(n_nt)]
    T = [f't{i}' for i in range(n_t)]
    prods = []
    for a in NT:
        for _ in range(rng.randint(1, 3)):
            if operator:
                L = rng.randint(1, 3); r = []
                prev_nt = False
                for _k in range(L):
                    if not prev_nt and rng.random() < 0.45:
                        r.append(rng.choice(NT)); prev_nt = True
                    else:
                        r.append(rng.choice(T)); prev_nt = False
            else:
                if rng.random() < eps_prob:
                    r = []
                else:
                    L = rng.randint(1, 4)
                    r = [rng.choice(NT) if rng.random() < 0.45 else rng.choice(T) for _ in range(L)]
            prods.append((a, tuple(r)))
    prods = list(dict.fromkeys(prods))
    # приведение: продуктивные и достижимые
    prod_ok = set(); changed = True
    while changed:
        changed = False
        for a, r in prods:
            if a not in prod_ok and all(s in prod_ok or s.startswith('t') for s in r):
                prod_ok.add(a); changed = True
    if 'A0' not in prod_ok:
        return None
    prods = [(a, r) for a, r in prods if a in prod_ok and all(s in prod_ok or s.startswith('t') for s in r)]
    reach = {'A0'}; changed = True
    while changed:
        changed = False
        for a, r in prods:
            if a in reach:
                for s in r:
                    if s.startswith('A') and s not in reach:
                        reach.add(s); changed = True
    prods = [(a, r) for a, r in prods if a in reach]
    prods.sort(key=lambda x: x[0] != 'A0')
    if len(prods) < 3 or not any(s.startswith('t') for _, r in prods for s in r):
        return None
    if any(r == ('A0',) and a == 'A0' for a, r in prods):
        pass
    return Grammar(prods, start='A0')


def lr1_closure(g: Grammar, la_init, cache):
    """LR(1)-замыкание: la_init — {(p, d): set(lookahead)}."""
    la = defaultdict(set)
    for k, v in la_init.items():
        la[k] |= v
    work = deque(la.keys())
    while work:
        p, d = work.popleft()
        r = g.prods[p][1]
        if d < len(r) and g.is_nt(r[d]):
            key = (p, d + 1)
            if key not in cache:
                cache[key] = g.first_seq(r[d + 1:])
            f, nul = cache[key]
            new = set(f)
            if nul:
                new |= la[(p, d)]
            for q in g.by_lhs[r[d]]:
                cur = la[(q, 0)]
                if not new <= cur:
                    cur |= new
                    work.append((q, 0))
    return la


class LALR1Prop(LRBase):
    """LALR(1) по LR(0)-автомату с распространением предпросмотров
    (спонтанная генерация и распространение, алгоритм Ахо—Сети—Ульмана).
    Не строит канонический LR(1)-автомат."""
    method = 'LALR(1)'

    def __init__(self, g: Grammar, lr0: LR0Automaton | None = None):
        self.g = g
        ga, _ = _augment(g); self.ga = ga
        A = lr0 or LR0Automaton(ga)
        self.nstates = len(A.kernels)
        HASH = '\x00#'
        cache = {}
        LA = {(s, it): set() for s, k in enumerate(A.kernels) for it in k}
        LA[(0, (0, 0))].add(END)
        prop = defaultdict(list)
        for s, kernel in enumerate(A.kernels):
            for it in kernel:
                cl = lr1_closure(ga, {it: {HASH}}, cache)
                for (p, d), las in cl.items():
                    r = ga.prods[p][1]
                    if d < len(r):
                        t = A.trans[(s, r[d])]
                        tgt = (t, (p, d + 1))
                        for a in las:
                            if a == HASH:
                                prop[(s, it)].append(tgt)
                            else:
                                LA[tgt].add(a)
        changed = True
        while changed:
            changed = False
            for src, tgts in prop.items():
                v = LA[src]
                if not v:
                    continue
                for t in tgts:
                    if not v <= LA[t]:
                        LA[t] |= v; changed = True
        acts = defaultdict(list); self.goto = {}
        for (s, X), t in A.trans.items():
            if ga.is_nt(X):
                self.goto[(s, X)] = t
            else:
                acts[(s, X)].append(('s', t))
        for s, kernel in enumerate(A.kernels):
            cl = lr1_closure(ga, {it: LA[(s, it)] for it in kernel}, cache)
            for (p, d), las in cl.items():
                if d == len(ga.prods[p][1]):
                    for a in las:
                        act = ('acc', 0) if p == 0 else ('r', p - 1)
                        if act not in acts[(s, a)]:
                            acts[(s, a)].append(act)
        self._finish(acts)

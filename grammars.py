"""Тестовые грамматики эксперимента (G1–G7)."""
from parsing_lab import Grammar

G1 = """
E -> E + T | E - T | T
T -> T * F | T / F | F
F -> ( E ) | id | num
"""

G2 = """
E -> T E'
E' -> + T E' | - T E' | eps
T -> F T'
T' -> * F T' | / F T' | eps
F -> ( E ) | id | num
"""

G3 = """
S -> L = R | R
L -> * R | id
R -> L
"""

G4 = """
S -> if C then S | if C then S else S | other
C -> id
"""

G5 = """
value -> object | array | str | num | true | false | null
object -> { members } | { }
members -> members , pair | pair
pair -> str : value
array -> [ elements ] | [ ]
elements -> elements , value | value
"""

G6 = """
program -> block .
block -> consts vars procs statement
consts -> const id = num constlist ; | eps
constlist -> , id = num constlist | eps
vars -> var id idlist ; | eps
idlist -> , id idlist | eps
procs -> procedure id ; block ; procs | eps
statement -> id := expression | call id | begin statement stmtlist end | if condition then statement | while condition do statement | eps
stmtlist -> ; statement stmtlist | eps
condition -> odd expression | expression relop expression
relop -> = | # | < | <= | > | >=
expression -> sign term termlist
sign -> + | - | eps
termlist -> addop term termlist | eps
addop -> + | -
term -> factor factorlist
factorlist -> mulop factor factorlist | eps
mulop -> * | /
factor -> id | num | ( expression )
"""

G7 = """
program -> decls
decls -> decls decl | decl
decl -> type id ( params ) block | type id ;
type -> int | void
params -> paramlist | eps
paramlist -> paramlist , type id | type id
block -> { stmts }
stmts -> stmts stmt | eps
stmt -> type id ; | expr ; | block | if ( expr ) block | if ( expr ) block else block | while ( expr ) block | return expr ; | return ;
expr -> id = expr | or
or -> or || and | and
and -> and && eq | eq
eq -> eq == rel | eq != rel | rel
rel -> rel < add | rel > add | rel <= add | rel >= add | add
add -> add + mul | add - mul | mul
mul -> mul * un | mul / un | mul % un | un
un -> ! un | - un | post
post -> id ( args ) | id | num | ( expr )
args -> arglist | eps
arglist -> arglist , expr | expr
"""

GRAMMARS = {
    'G1': ('Арифм. выражения (леворекурсивная)', G1),
    'G2': ('Арифм. выражения (LL-форма)', G2),
    'G3': ('Присваивание с указателями', G3),
    'G4': ('Висячий else', G4),
    'G5': ('JSON', G5),
    'G6': ('PL/0 (Вирт)', G6),
    'G7': ('Подмножество C', G7),
}


def load():
    return {k: Grammar.parse(t, name=k) for k, (_, t) in GRAMMARS.items()}

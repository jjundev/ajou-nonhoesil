import re

_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_]*|[()'+·⊕]")


class _Parser:
    """재귀 하강. 우선순위 낮음 → 높음:

        expr   := xor ( '+' xor )*
        xor    := term ( '⊕' term )*
        term   := factor ( '·' factor )*
        factor := atom "'"*
        atom   := NAME | '(' expr ')'
    """

    def __init__(self, text, env):
        self.toks = _TOKEN.findall(text)
        self.i = 0
        self.env = env

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def eat(self, expect=None):
        cur = self.peek()
        if expect is not None and cur != expect:
            raise ValueError(f"{expect!r} 를 기대했지만 {cur!r} 를 만났습니다")
        self.i += 1
        return cur

    def expr(self):
        v = self.xor()
        while self.peek() == "+":
            self.eat()
            v |= self.xor()
        return v

    def xor(self):
        v = self.term()
        while self.peek() == "⊕":
            self.eat()
            v ^= self.term()
        return v

    def term(self):
        v = self.factor()
        while self.peek() == "·":
            self.eat()
            v &= self.factor()
        return v

    def factor(self):
        v = self.atom()
        while self.peek() == "'":
            self.eat()
            v = 1 - v
        return v

    def atom(self):
        tok = self.eat()
        if tok == "(":
            v = self.expr()
            self.eat(")")
            return v
        if tok is None or not tok[0].isalpha():
            raise ValueError(f"예상치 못한 토큰: {tok!r}")
        if tok not in self.env:
            raise ValueError(f"입력 변수 {tok!r} 이(가) 표에 없습니다")
        return 1 if self.env[tok] else 0


def eval_boolean(text, env):
    p = _Parser(text, env)
    v = p.expr()
    if p.peek() is not None:
        raise ValueError(f"식 끝에 남은 토큰: {p.peek()!r}")
    return v

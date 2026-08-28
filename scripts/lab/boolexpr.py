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
        # `findall` 은 인식 못 한 문자를 **조용히 버린다** — `!A` 가 `A` 로 평가돼
        # 틀린 진리표를 통과시킨다. 빈틈이 있으면 거절한다.
        self.toks, pos = [], 0
        for m in _TOKEN.finditer(text):
            gap = text[pos:m.start()]
            if gap.strip():
                raise ValueError(f"알 수 없는 문자: {gap.strip()!r} (식: {text!r})")
            self.toks.append(m.group(0))
            pos = m.end()
        if text[pos:].strip():
            raise ValueError(f"알 수 없는 문자: {text[pos:].strip()!r} (식: {text!r})")
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

const inputPins = ['CLK', 'J', 'K', 'PR', 'CLR'];
const jkRules = [
  'JK=00이라 이전 Q를 유지해요.',
  'JK=01이라 Q를 0으로 만들어요.',
  'JK=10이라 Q를 1로 만들어요.',
  'JK=11이라 이전 Q를 뒤집어요.',
];

export function transition(previous, {pin, value}) {
  if (!inputPins.includes(pin) || ![0, 1].includes(value)) {
    return {next: previous, accepted: false, reason: '입력 핀에 0 또는 1을 주세요.'};
  }

  const next = {...previous, [pin]: value};
  if (next.PR === 0 && next.CLR === 0) {
    return {
      next: previous,
      accepted: false,
      reason: 'PR과 CLR을 동시에 0으로 두는 조합은 이 실험의 범위 밖이에요.',
    };
  }

  let reason;
  let rule;
  if (next.PR === 0) {
    next.Q = 1;
    rule = 'pr';
    reason = 'PR=0이므로 클럭과 관계없이 Q를 1로 만들어요.';
  } else if (next.CLR === 0) {
    next.Q = 0;
    rule = 'clr';
    reason = 'CLR=0이므로 클럭과 관계없이 Q를 0으로 만들어요.';
  } else if (previous.CLK === 1 && next.CLK === 0) {
    const jk = 2 * next.J + next.K;
    next.Q = [previous.Q, 0, 1, 1 - previous.Q][jk];
    rule = 'jk' + next.J + next.K;
    reason = '하강 엣지(1→0)에서 ' + jkRules[jk];
  } else if (previous.CLK === 0 && next.CLK === 1) {
    rule = 'rising';
    reason = '상승 엣지(0→1)에서는 이전 Q를 유지해요.';
  } else {
    rule = next.CLK === 0 ? 'low' : 'high';
    reason = '하강 엣지가 없으므로 이전 Q를 유지해요.';
  }

  return {next, accepted: true, rule, reason};
}

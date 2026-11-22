export function transition(previous, {pin, value}) {
  if (!['D', 'E'].includes(pin) || ![0, 1].includes(value)) {
    return {next: previous, accepted: false, reason: 'D 또는 E에 0이나 1을 주세요.'};
  }

  const next = {...previous, [pin]: value};
  if (next.E === 0) {
    return {next, accepted: true, rule: 'hold', reason: 'E=0이면 Q는 이전 값을 유지해요.'};
  }

  next.Q = next.D;
  return {
    next,
    accepted: true,
    rule: next.D === 1 ? 'set' : 'reset',
    reason: 'E=1 동안 Q가 D=' + next.D + '를 따라가요.',
  };
}

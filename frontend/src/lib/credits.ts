export function creditShortfall(available: number, required: number) {
  return Math.max(0, required - available);
}

export function canAffordGeneration(
  available: number | undefined,
  required: number | undefined,
) {
  return available !== undefined && required !== undefined && available >= required;
}

export function creditActivityAmount(balanceDelta: number, reservedDelta: number) {
  return balanceDelta || reservedDelta;
}

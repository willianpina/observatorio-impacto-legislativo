/** Só texto pode conter fórmula; números negativos devem permanecer numéricos. */
export function csvCell(value: unknown): string {
  const safe = typeof value === 'string' ? value.replace(/^[=+\-@\t\r]/, "'$&") : String(value ?? '');
  return `"${safe.replaceAll('"', '""')}"`;
}

/**
 * utils/formatters.ts
 * Strict INR and number formatting without calculation, alteration, or rounding.
 * Rule 1: Show numbers exactly as received. No recalculation, re-ranking,
 * client-side thresholds or hidden rounding. Formatting only through formatInr().
 */

export function formatInr(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) {
    return String(value);
  }

  // Format as Indian Rupee representation (e.g. ₹2,450 or ₹2,450.50)
  // Preserves exact decimal places received without artificial client-side rounding
  const parts = num.toString().split('.');
  const integerPart = parts[0];
  const decimalPart = parts[1] !== undefined ? `.${parts[1]}` : '';

  // Indian numbering regex: last 3 digits, then groups of 2
  const isNegative = integerPart.startsWith('-');
  const absInt = isNegative ? integerPart.slice(1) : integerPart;

  const lastThree = absInt.substring(absInt.length - 3);
  const otherNumbers = absInt.substring(0, absInt.length - 3);
  const formattedInteger = otherNumbers !== ''
    ? otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + lastThree
    : lastThree;

  const sign = isNegative ? '-' : '';
  return `${sign}₹${formattedInteger}${decimalPart}`;
}

export function formatNumber(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return String(value);

  const parts = num.toString().split('.');
  const lastThree = parts[0].substring(parts[0].length - 3);
  const otherNumbers = parts[0].substring(0, parts[0].length - 3);
  const formatted = otherNumbers !== ''
    ? otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + lastThree
    : lastThree;
  return parts[1] !== undefined ? `${formatted}.${parts[1]}` : formatted;
}

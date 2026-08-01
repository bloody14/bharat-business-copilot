/**
 * Format a number using Indian digit grouping (lakhs/crores).
 * e.g. 125000 → "1,25,000"
 */
export function formatIndianNumber(value: number | string): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "0";
  
  const [intPart, decPart] = num.toString().split(".");
  const isNegative = intPart.startsWith("-");
  const absInt = isNegative ? intPart.slice(1) : intPart;
  
  if (absInt.length <= 3) {
    const formatted = absInt + (decPart ? `.${decPart}` : "");
    return isNegative ? `-${formatted}` : formatted;
  }
  
  // Last 3 digits, then groups of 2
  const lastThree = absInt.slice(-3);
  const remaining = absInt.slice(0, -3);
  const groups = remaining.replace(/\B(?=(\d{2})+(?!\d))/g, ",");
  const formatted = `${groups},${lastThree}${decPart ? `.${decPart}` : ""}`;
  return isNegative ? `-${formatted}` : formatted;
}

/**
 * Format a value as Indian Rupees.
 * e.g. 125000 → "₹1,25,000"
 */
export function formatRupees(value: number | string): string {
  return `₹${formatIndianNumber(value)}`;
}

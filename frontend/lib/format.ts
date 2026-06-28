/** Форматирование денег: «1 234 567 ₽». Валюта — ISO-код из бэкенда. */
const SYMBOLS: Record<string, string> = {
  RUB: "₽",
  USD: "$",
  EUR: "€",
  GBP: "£",
  PLN: "zł",
  AED: "AED",
  TRY: "₺",
  KZT: "₸",
  CAD: "C$",
  AUD: "A$",
  CHF: "CHF",
};

export function money(amount: number, currency: string): string {
  const rounded = Math.round(amount);
  const grouped = new Intl.NumberFormat("ru-RU").format(rounded);
  const sym = SYMBOLS[currency];
  if (!sym) return `${grouped} ${currency}`;
  // Символы валют ставим после числа в русской типографике.
  return `${grouped} ${sym}`;
}

export function compactMoney(amount: number, currency: string): string {
  const abs = Math.abs(amount);
  const sym = SYMBOLS[currency] ?? currency;
  const sign = amount < 0 ? "−" : "";
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)} млн ${sym}`;
  if (abs >= 1_000) return `${sign}${Math.round(abs / 1_000)} тыс ${sym}`;
  return `${sign}${Math.round(abs)} ${sym}`;
}

export function pct(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

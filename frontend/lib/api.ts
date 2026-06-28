import type { AnalyzeResponse, Overrides } from "./types";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export class AnalyzeError extends Error {}

/** Серверный вызов бэкенда (используется в server component при SSR). */
export async function analyze(
  address: string,
  overrides: Overrides = {},
): Promise<AnalyzeResponse> {
  let resp: Response;
  try {
    resp = await fetch(`${BACKEND_URL}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address, overrides }),
      cache: "no-store",
    });
  } catch {
    throw new AnalyzeError("Не удалось связаться с сервисом расчёта. Запущен ли бэкенд?");
  }

  if (resp.status === 422) {
    const data = await resp.json().catch(() => null);
    const detail =
      data && typeof data.detail === "string"
        ? data.detail
        : "Не удалось распознать адрес. Уточните запрос.";
    throw new AnalyzeError(detail);
  }
  if (!resp.ok) {
    throw new AnalyzeError(`Сервис вернул ошибку (${resp.status}).`);
  }
  return (await resp.json()) as AnalyzeResponse;
}

"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import type { AssumptionsOut } from "@/lib/types";

interface Props {
  address: string;
  assumptions: AssumptionsOut;
}

// Поля, которые показываем как проценты (в URL и бэкенд уходят долями).
const PCT_FIELDS = [
  "down_payment_pct",
  "mortgage_rate",
  "property_tax_rate",
  "maintenance_rate",
  "home_appreciation",
  "rent_growth",
  "investment_return",
] as const;

type Field = {
  key: keyof AssumptionsOut;
  label: string;
  kind: "money" | "pct" | "int";
};

const FIELDS: Field[] = [
  { key: "area_sqm", label: "Площадь, м²", kind: "int" },
  { key: "horizon_years", label: "Срок проживания, лет", kind: "int" },
  { key: "home_price", label: "Цена покупки", kind: "money" },
  { key: "monthly_rent", label: "Аренда в месяц", kind: "money" },
  { key: "down_payment_pct", label: "Первый взнос, %", kind: "pct" },
  { key: "mortgage_rate", label: "Ставка ипотеки, %", kind: "pct" },
  { key: "loan_term_years", label: "Срок ипотеки, лет", kind: "int" },
  { key: "home_appreciation", label: "Рост цен на жильё, %/год", kind: "pct" },
  { key: "rent_growth", label: "Рост аренды, %/год", kind: "pct" },
  { key: "investment_return", label: "Доходность вложений, %/год", kind: "pct" },
  { key: "property_tax_rate", label: "Налог на недвижимость, %/год", kind: "pct" },
  { key: "maintenance_rate", label: "Содержание, %/год", kind: "pct" },
];

function toDisplay(field: Field, value: number): string {
  if (field.kind === "pct") return (value * 100).toFixed(2).replace(/\.?0+$/, "");
  return String(Math.round(value));
}

export default function AssumptionsForm({ address, assumptions }: Props) {
  const router = useRouter();
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const f of FIELDS) init[f.key] = toDisplay(f, assumptions[f.key] as number);
    return init;
  });

  function update(key: string, v: string) {
    setValues((prev) => ({ ...prev, [key]: v }));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const params = new URLSearchParams();
    params.set("address", address);
    for (const f of FIELDS) {
      const raw = values[f.key]?.trim().replace(",", ".");
      if (raw === "" || raw == null) continue;
      const num = Number(raw);
      if (!Number.isFinite(num)) continue;
      const isPct = (PCT_FIELDS as readonly string[]).includes(f.key);
      params.set(f.key, String(isPct ? num / 100 : num));
    }
    router.push(`/?${params.toString()}`);
  }

  function reset() {
    router.push(`/?address=${encodeURIComponent(address)}`);
  }

  return (
    <div className="section">
      <h3>Допущения расчёта</h3>
      <p className="hint">
        Цифры — рыночные ориентиры для этой локации. Подставьте свои значения — расчёт
        пересчитается мгновенно.
      </p>

      <form onSubmit={submit}>
        <div className="assump-grid">
          {FIELDS.map((f) => (
            <div className="field" key={f.key}>
              <label htmlFor={f.key}>{f.label}</label>
              <input
                id={f.key}
                type="text"
                inputMode="decimal"
                value={values[f.key] ?? ""}
                onChange={(e) => update(f.key, e.target.value)}
              />
            </div>
          ))}
        </div>
        <div className="form-actions">
          <button className="btn" type="submit">
            Пересчитать
          </button>
          <button className="btn secondary" type="button" onClick={reset}>
            Сбросить
          </button>
        </div>
      </form>
    </div>
  );
}

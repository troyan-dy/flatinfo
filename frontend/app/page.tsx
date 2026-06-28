import { Suspense } from "react";
import type { Overrides } from "@/lib/types";
import ResultView from "./ResultView";
import ResultSkeleton from "./ResultSkeleton";
import SearchBox from "./SearchBox";

export const dynamic = "force-dynamic";

const EXAMPLES = [
  "Москва, Тверская 7",
  "Санкт-Петербург, Невский проспект 28",
  "Berlin, Alexanderplatz",
  "Dubai Marina",
];

const OVERRIDE_KEYS = [
  "area_sqm",
  "horizon_years",
  "home_price",
  "monthly_rent",
  "down_payment_pct",
  "mortgage_rate",
  "loan_term_years",
  "property_tax_rate",
  "maintenance_rate",
  "home_appreciation",
  "rent_growth",
  "investment_return",
] as const;

type SearchParams = Record<string, string | string[] | undefined>;

function parseOverrides(sp: SearchParams): Overrides {
  const ov: Overrides = {};
  for (const key of OVERRIDE_KEYS) {
    const raw = sp[key];
    const val = Array.isArray(raw) ? raw[0] : raw;
    if (val == null || val === "") continue;
    const num = Number(val);
    if (Number.isFinite(num)) (ov as Record<string, number>)[key] = num;
  }
  return ov;
}

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const addressRaw = sp.address;
  const address = (Array.isArray(addressRaw) ? addressRaw[0] : addressRaw)?.trim() ?? "";
  const overrides = parseOverrides(sp);

  // Ключ пересоздаёт Suspense-границу при каждом новом запросе → показывается скелетон.
  const suspenseKey = JSON.stringify({ address, overrides });

  return (
    <main className="container">
      <div className="brand">
        <div className="brand-logo">🏠</div>
        <h1>flatinfo</h1>
      </div>
      <p className="lede">
        Введите адрес — посчитаем, что выгоднее по деньгам за годы жизни: снимать жильё
        или купить в ипотеку. Сравнение честное: учитываем рост цен, аренды и доход от
        альтернативных вложений.
      </p>

      <SearchBox defaultAddress={address} />

      <div className="examples">
        <span>Примеры:</span>
        {EXAMPLES.map((ex) => (
          <a key={ex} className="chip" href={`/?address=${encodeURIComponent(ex)}`}>
            {ex}
          </a>
        ))}
      </div>

      {address ? (
        <Suspense key={suspenseKey} fallback={<ResultSkeleton />}>
          <ResultView address={address} overrides={overrides} />
        </Suspense>
      ) : (
        <div className="section how">
          <h3>Как мы считаем</h3>
          <ol className="how-steps">
            <li>
              <b>По адресу</b> определяем город и страну и подбираем рыночные ориентиры:
              цену и аренду за м², ставку ипотеки, налог, рост цен и аренды.
            </li>
            <li>
              <b>Сравниваем два сценария</b> при одинаковом бюджете: один покупает в
              ипотеку, другой снимает и инвестирует сэкономленные деньги (включая первый
              взнос).
            </li>
            <li>
              <b>Считаем итоговый капитал</b> через выбранный срок: у покупателя — жильё
              за вычетом долга и расходов на продажу, у арендатора — портфель вложений.
              Кто богаче — тому и вердикт.
            </li>
          </ol>
          <p className="hint" style={{ marginBottom: 0 }}>
            Любую цифру можно поправить под себя — расчёт пересчитается.
          </p>
        </div>
      )}

      <div className="footer">
        flatinfo — оценка, а не инвестиционный совет. Рыночные цифры приблизительны;
        для точного решения подставьте реальные цену, аренду и ставку.
      </div>
    </main>
  );
}

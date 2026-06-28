import { analyze, AnalyzeError } from "@/lib/api";
import type { Overrides } from "@/lib/types";
import { money, pct } from "@/lib/format";
import NetWorthChart from "./NetWorthChart";
import AssumptionsForm from "./AssumptionsForm";

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

const REC_LABEL: Record<string, string> = {
  buy: "Выгоднее покупать",
  rent: "Выгоднее снимать",
  neutral: "Примерно поровну",
};

const SOURCE_NOTE: Record<string, string> = {
  city: "Оценка для конкретного города",
  country: "Оценка по стране (нет точных данных по городу) — проверьте цены и аренду",
  global: "Глобальная усреднённая оценка — обязательно подставьте реальные цифры",
};

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const addressRaw = sp.address;
  const address = (Array.isArray(addressRaw) ? addressRaw[0] : addressRaw)?.trim() ?? "";
  const overrides = parseOverrides(sp);

  let data = null;
  let error: string | null = null;
  if (address) {
    try {
      data = await analyze(address, overrides);
    } catch (e) {
      error = e instanceof AnalyzeError ? e.message : "Неожиданная ошибка расчёта.";
    }
  }

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

      <form className="search" method="GET" action="/">
        <input
          type="text"
          name="address"
          placeholder="Например: Москва, Тверская 7"
          defaultValue={address}
          autoComplete="off"
          autoFocus
        />
        <button className="btn" type="submit">
          Посчитать
        </button>
      </form>

      <div className="examples">
        <span>Примеры:</span>
        {EXAMPLES.map((ex) => (
          <a key={ex} className="chip" href={`/?address=${encodeURIComponent(ex)}`}>
            {ex}
          </a>
        ))}
      </div>

      {error && <div className="error">{error}</div>}

      {data && (
        <>
          <div className={`verdict ${data.result.recommendation}`}>
            <span className="verdict-tag">{REC_LABEL[data.result.recommendation]}</span>
            <h2>{REC_LABEL[data.result.recommendation]}</h2>
            <div className="addr">{data.location.display_name}</div>
            <p className="summary">{data.summary}</p>

            <div className="metrics">
              <div className="metric">
                <div className="label">Капитал через {data.result.horizon_years} лет — покупка</div>
                <div className="value buy">
                  {money(data.result.buy_net_worth, data.assumptions.currency)}
                </div>
              </div>
              <div className="metric">
                <div className="label">Капитал через {data.result.horizon_years} лет — аренда</div>
                <div className="value rent">
                  {money(data.result.rent_net_worth, data.assumptions.currency)}
                </div>
              </div>
              <div className="metric">
                <div className="label">Точка окупаемости покупки</div>
                <div className="value">
                  {data.result.break_even_year
                    ? `${data.result.break_even_year}-й год`
                    : "за горизонтом"}
                </div>
              </div>
              <div className="metric">
                <div className="label">Платёж по ипотеке</div>
                <div className="value">
                  {money(data.result.monthly_mortgage, data.assumptions.currency)}/мес
                </div>
              </div>
            </div>
          </div>

          <div className="section">
            <h3>Как расходится капитал со временем</h3>
            <p className="hint">
              Линии — итоговое богатство в каждом сценарии: стоимость жилья за вычетом
              остатка кредита и расходов на продажу (покупка) против вложенного первого
              взноса и сэкономленной разницы (аренда).
            </p>
            <NetWorthChart
              timeline={data.result.timeline}
              currency={data.assumptions.currency}
              breakEvenYear={data.result.break_even_year}
            />
          </div>

          <div className="section">
            <h3>Исходные данные</h3>
            <p className="hint">Оценки рынка для этой локации, на которых построен расчёт.</p>
            <table className="breakdown">
              <tbody>
                <tr>
                  <td>Площадь</td>
                  <td>{Math.round(data.assumptions.area_sqm)} м²</td>
                </tr>
                <tr>
                  <td>Цена покупки</td>
                  <td>{money(data.assumptions.home_price, data.assumptions.currency)}</td>
                </tr>
                <tr>
                  <td>Аренда в месяц</td>
                  <td>{money(data.assumptions.monthly_rent, data.assumptions.currency)}</td>
                </tr>
                <tr>
                  <td>Ставка ипотеки</td>
                  <td>{pct(data.assumptions.mortgage_rate)}</td>
                </tr>
                <tr>
                  <td>Первый взнос</td>
                  <td>{pct(data.assumptions.down_payment_pct)}</td>
                </tr>
                <tr>
                  <td>Рост цен на жильё</td>
                  <td>{pct(data.assumptions.home_appreciation)}/год</td>
                </tr>
                <tr>
                  <td>Рост аренды</td>
                  <td>{pct(data.assumptions.rent_growth)}/год</td>
                </tr>
                <tr>
                  <td>Доходность вложений</td>
                  <td>{pct(data.assumptions.investment_return)}/год</td>
                </tr>
              </tbody>
            </table>
            <div className="source-note">{SOURCE_NOTE[data.assumptions.data_source]}</div>
          </div>

          <AssumptionsForm address={address} assumptions={data.assumptions} />
        </>
      )}

      <div className="footer">
        flatinfo — оценка, а не инвестиционный совет. Рыночные цифры приблизительны;
        для точного решения подставьте реальные цену, аренду и ставку.
      </div>
    </main>
  );
}

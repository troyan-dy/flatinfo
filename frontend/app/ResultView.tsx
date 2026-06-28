import { analyze, AnalyzeError } from "@/lib/api";
import type { Overrides } from "@/lib/types";
import { money, pct } from "@/lib/format";
import NetWorthChart from "./NetWorthChart";
import AssumptionsForm from "./AssumptionsForm";

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

function headline(rec: string, advantage: number, horizon: number, currency: string): string {
  const sum = money(Math.abs(advantage), currency);
  if (rec === "buy") return `Покупка выгоднее на ${sum}`;
  if (rec === "rent") return `Аренда выгоднее на ${sum}`;
  return `Разница всего ${sum} за ${horizon} лет`;
}

export default async function ResultView({
  address,
  overrides,
}: {
  address: string;
  overrides: Overrides;
}) {
  let data = null;
  let error: string | null = null;
  try {
    data = await analyze(address, overrides);
  } catch (e) {
    error = e instanceof AnalyzeError ? e.message : "Неожиданная ошибка расчёта.";
  }

  if (error) return <div className="error">{error}</div>;
  if (!data) return null;

  const { result, assumptions, location } = data;
  const cur = assumptions.currency;

  return (
    <>
      <div className={`verdict ${result.recommendation}`}>
        <span className="verdict-tag">{REC_LABEL[result.recommendation]}</span>
        <h2>{headline(result.recommendation, result.advantage, result.horizon_years, cur)}</h2>
        <div className="addr">{location.display_name}</div>
        <p className="summary">{data.summary}</p>

        <div className="metrics">
          <div className="metric">
            <div className="label">Капитал через {result.horizon_years} лет — покупка</div>
            <div className="value buy">{money(result.buy_net_worth, cur)}</div>
          </div>
          <div className="metric">
            <div className="label">Капитал через {result.horizon_years} лет — аренда</div>
            <div className="value rent">{money(result.rent_net_worth, cur)}</div>
          </div>
          <div className="metric">
            <div className="label">Точка окупаемости покупки</div>
            <div className="value">
              {result.break_even_year ? `${result.break_even_year}-й год` : "за горизонтом"}
            </div>
          </div>
          <div className="metric">
            <div className="label">Платёж по ипотеке</div>
            <div className="value">{money(result.monthly_mortgage, cur)}/мес</div>
          </div>
        </div>
      </div>

      <div className="section">
        <h3>Как расходится капитал со временем</h3>
        <p className="hint">
          Линии — итоговое богатство в каждом сценарии: стоимость жилья за вычетом остатка
          кредита и расходов на продажу (покупка) против вложенного первого взноса и
          сэкономленной разницы (аренда).
        </p>
        <NetWorthChart
          timeline={result.timeline}
          currency={cur}
          breakEvenYear={result.break_even_year}
        />
      </div>

      <div className="section">
        <h3>Что куда уходит за {result.horizon_years} лет</h3>
        <p className="hint">Суммарные платежи в каждом сценарии (без учёта роста капитала).</p>
        <table className="breakdown">
          <tbody>
            <tr>
              <td>Всего платежей при покупке</td>
              <td>{money(result.total_buy_cost, cur)}</td>
            </tr>
            <tr>
              <td>Всего аренды</td>
              <td>{money(result.total_rent_cost, cur)}</td>
            </tr>
            <tr>
              <td>Стоимость жилья к концу срока</td>
              <td>{money(result.timeline[result.timeline.length - 1].home_value, cur)}</td>
            </tr>
            <tr>
              <td>Капитал в жилье к концу срока</td>
              <td>{money(result.timeline[result.timeline.length - 1].home_equity, cur)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="section">
        <h3>Исходные данные</h3>
        <p className="hint">Оценки рынка для этой локации, на которых построен расчёт.</p>
        <table className="breakdown">
          <tbody>
            <tr>
              <td>Площадь</td>
              <td>{Math.round(assumptions.area_sqm)} м²</td>
            </tr>
            <tr>
              <td>Цена покупки</td>
              <td>{money(assumptions.home_price, cur)}</td>
            </tr>
            <tr>
              <td>Аренда в месяц</td>
              <td>{money(assumptions.monthly_rent, cur)}</td>
            </tr>
            <tr>
              <td>Ставка ипотеки</td>
              <td>{pct(assumptions.mortgage_rate)}</td>
            </tr>
            <tr>
              <td>Первый взнос</td>
              <td>{pct(assumptions.down_payment_pct)}</td>
            </tr>
            <tr>
              <td>Рост цен на жильё</td>
              <td>{pct(assumptions.home_appreciation)}/год</td>
            </tr>
            <tr>
              <td>Рост аренды</td>
              <td>{pct(assumptions.rent_growth)}/год</td>
            </tr>
            <tr>
              <td>Доходность вложений</td>
              <td>{pct(assumptions.investment_return)}/год</td>
            </tr>
          </tbody>
        </table>
        <div className="source-note">{SOURCE_NOTE[assumptions.data_source]}</div>
      </div>

      <AssumptionsForm address={address} assumptions={assumptions} />
    </>
  );
}

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

function headline(rec: string, advantage: number, horizon: number, currency: string): string {
  const sum = money(Math.abs(advantage), currency);
  if (rec === "buy") return `Покупка выгоднее на ${sum}`;
  if (rec === "rent") return `Аренда выгоднее на ${sum}`;
  return `Разница всего ${sum} за ${horizon} лет`;
}

/** Контекстные причины вердикта по соотношениям входных параметров. */
function reasons(a: {
  home_price: number;
  monthly_rent: number;
  mortgage_rate: number;
  home_appreciation: number;
  investment_return: number;
}): string[] {
  const out: string[] = [];
  const ratio = a.home_price / (a.monthly_rent * 12); // цена / годовая аренда
  if (ratio >= 25) {
    out.push(
      `Жильё дорогое относительно аренды: цена ≈ ${ratio.toFixed(0)} годовых аренд (> 25) — снимать дёшево.`,
    );
  } else if (ratio <= 15) {
    out.push(
      `Аренда дорогая относительно цены: цена ≈ ${ratio.toFixed(0)} годовых аренд (< 15) — покупка окупается быстро.`,
    );
  } else {
    out.push(`Цена ≈ ${ratio.toFixed(0)} годовых аренд — пограничное соотношение.`);
  }

  if (a.investment_return - a.home_appreciation >= 0.03) {
    out.push(
      `Вложения доходнее роста жилья (${pct(a.investment_return, 0)} против ${pct(a.home_appreciation, 0)}/год) — деньги выгоднее инвестировать, чем держать в недвижимости.`,
    );
  } else if (a.home_appreciation - a.investment_return >= 0.01) {
    out.push(
      `Жильё растёт быстрее типичных вложений (${pct(a.home_appreciation, 0)} против ${pct(a.investment_return, 0)}/год) — в пользу покупки.`,
    );
  }

  if (a.mortgage_rate >= 0.12) {
    out.push(`Высокая ставка ипотеки (${pct(a.mortgage_rate, 0)}) удорожает покупку.`);
  } else if (a.mortgage_rate <= 0.05) {
    out.push(`Низкая ставка ипотеки (${pct(a.mortgage_rate, 0)}) делает кредит дешёвым.`);
  }
  return out;
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
        <h3>Почему так</h3>
        <p className="hint">Главные факторы, повлиявшие на вердикт.</p>
        <ul className="reasons">
          {reasons(assumptions).map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
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

      <AssumptionsForm address={address} assumptions={assumptions} />
    </>
  );
}

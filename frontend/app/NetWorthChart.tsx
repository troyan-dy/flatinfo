"use client";

import { useState } from "react";
import type { YearPointOut } from "@/lib/types";
import { compactMoney, money } from "@/lib/format";

interface Props {
  timeline: YearPointOut[];
  currency: string;
  breakEvenYear: number | null;
}

const W = 760;
const H = 280;
const PAD = { top: 20, right: 16, bottom: 30, left: 78 };

export default function NetWorthChart({ timeline, currency, breakEvenYear }: Props) {
  const [hover, setHover] = useState<number | null>(null);

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const years = timeline.map((p) => p.year);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const allValues = timeline.flatMap((p) => [p.buy_net_worth, p.rent_net_worth]);
  const minV = Math.min(0, ...allValues);
  const maxV = Math.max(...allValues);
  const span = maxV - minV || 1;

  const x = (year: number) =>
    PAD.left + ((year - minYear) / Math.max(1, maxYear - minYear)) * innerW;
  const y = (v: number) => PAD.top + innerH - ((v - minV) / span) * innerH;

  const line = (key: "buy_net_worth" | "rent_net_worth") =>
    timeline.map((p, i) => `${i === 0 ? "M" : "L"}${x(p.year)},${y(p[key])}`).join(" ");

  const area = (key: "buy_net_worth" | "rent_net_worth") => {
    const top = timeline.map((p) => `L${x(p.year)},${y(p[key])}`).join(" ");
    return `M${x(timeline[0].year)},${y(minV)} ${top} L${x(maxYear)},${y(minV)} Z`;
  };

  // Горизонтальные линии сетки.
  const ticks = 4;
  const gridLines = Array.from({ length: ticks + 1 }, (_, i) => {
    const v = minV + (span * i) / ticks;
    return { v, y: y(v) };
  });

  const active = hover != null ? timeline[hover] : null;

  return (
    <div>
      <div className="legend">
        <span>
          <i className="dot buy" /> Покупка — итоговый капитал
        </span>
        <span>
          <i className="dot rent" /> Аренда + инвестиции
        </span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label="Динамика капитала: покупка против аренды"
        style={{ display: "block" }}
        onMouseLeave={() => setHover(null)}
      >
        {gridLines.map((g, i) => (
          <g key={i}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={g.y}
              y2={g.y}
              stroke="var(--border)"
              strokeWidth={1}
            />
            <text x={PAD.left - 8} y={g.y + 4} textAnchor="end" fontSize={11} fill="var(--muted)">
              {compactMoney(g.v, currency)}
            </text>
          </g>
        ))}

        {/* подписи по оси X */}
        {timeline
          .filter((_, i) => i % Math.ceil(timeline.length / 8) === 0 || i === timeline.length - 1)
          .map((p) => (
            <text
              key={p.year}
              x={x(p.year)}
              y={H - 10}
              textAnchor="middle"
              fontSize={11}
              fill="var(--muted)"
            >
              {p.year} г.
            </text>
          ))}

        {/* точка окупаемости */}
        {breakEvenYear != null && breakEvenYear >= minYear && breakEvenYear <= maxYear && (
          <line
            x1={x(breakEvenYear)}
            x2={x(breakEvenYear)}
            y1={PAD.top}
            y2={H - PAD.bottom}
            stroke="var(--neutral)"
            strokeWidth={1}
            strokeDasharray="4 4"
          />
        )}

        <defs>
          <linearGradient id="gbuy" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--buy)" stopOpacity="0.25" />
            <stop offset="100%" stopColor="var(--buy)" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="grent" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--rent)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--rent)" stopOpacity="0" />
          </linearGradient>
        </defs>

        <path d={area("rent_net_worth")} fill="url(#grent)" />
        <path d={area("buy_net_worth")} fill="url(#gbuy)" />
        <path d={line("rent_net_worth")} fill="none" stroke="var(--rent)" strokeWidth={2.5} />
        <path d={line("buy_net_worth")} fill="none" stroke="var(--buy)" strokeWidth={2.5} />

        {/* интерактивный слой */}
        {timeline.map((p, i) => (
          <rect
            key={p.year}
            x={x(p.year) - innerW / timeline.length / 2}
            y={PAD.top}
            width={innerW / timeline.length}
            height={innerH}
            fill="transparent"
            onMouseEnter={() => setHover(i)}
          />
        ))}

        {active && (
          <g>
            <line
              x1={x(active.year)}
              x2={x(active.year)}
              y1={PAD.top}
              y2={H - PAD.bottom}
              stroke="var(--muted)"
              strokeWidth={1}
              opacity={0.5}
            />
            <circle cx={x(active.year)} cy={y(active.buy_net_worth)} r={4} fill="var(--buy)" />
            <circle cx={x(active.year)} cy={y(active.rent_net_worth)} r={4} fill="var(--rent)" />
          </g>
        )}
      </svg>

      {active && (
        <div
          style={{
            marginTop: 8,
            fontSize: 14,
            color: "var(--muted)",
            display: "flex",
            gap: 18,
            flexWrap: "wrap",
          }}
        >
          <span>
            <b style={{ color: "var(--text)" }}>{active.year}-й год:</b>
          </span>
          <span>
            <i className="dot buy" /> покупка{" "}
            <b style={{ color: "var(--buy)" }}>{money(active.buy_net_worth, currency)}</b>
          </span>
          <span>
            <i className="dot rent" /> аренда{" "}
            <b style={{ color: "var(--rent)" }}>{money(active.rent_net_worth, currency)}</b>
          </span>
        </div>
      )}
    </div>
  );
}

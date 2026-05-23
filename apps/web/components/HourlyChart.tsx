"use client";

import {
  CartesianGrid,
  Dot,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatUAH } from "@/lib/format";

export interface HourlyPoint {
  /** ISO timestamp or hour label */
  ts: string;
  /** Display label, e.g. "12.05 14:00" */
  label?: string;
  /** Price (UAH/MWh) or other Y value */
  value: number;
  /** Whether the price is at the cap on this hour */
  is_capped?: boolean;
}

export interface HourlyChartProps {
  data: HourlyPoint[];
  cap?: number | null;
  height?: number;
  unit?: string;
  yLabel?: string;
}

interface CapDotProps {
  cx?: number;
  cy?: number;
  payload?: HourlyPoint;
}

function CapDot({ cx, cy, payload }: CapDotProps) {
  if (cx === undefined || cy === undefined || !payload) return null;
  const capped = payload.is_capped;
  return (
    <Dot
      cx={cx}
      cy={cy}
      r={capped ? 4 : 2}
      fill={capped ? "var(--color-alert)" : "var(--color-accent)"}
      stroke={capped ? "var(--color-alert)" : "var(--color-accent-deep)"}
      strokeWidth={1}
    />
  );
}

export function HourlyChart({
  data,
  cap,
  height = 280,
  unit = "грн/МВт·год",
  yLabel,
}: HourlyChartProps) {
  if (!data.length) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-border text-sm text-text-muted"
        style={{ height }}
      >
        Немає даних для відображення.
      </div>
    );
  }
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <LineChart
          data={data}
          margin={{ top: 10, right: 16, left: 0, bottom: 8 }}
        >
          <CartesianGrid
            stroke="var(--color-border)"
            strokeDasharray="3 3"
            vertical={false}
          />
          <XAxis
            dataKey="label"
            stroke="var(--color-text-muted)"
            tick={{ fontSize: 11 }}
            interval="preserveStartEnd"
            minTickGap={32}
          />
          <YAxis
            stroke="var(--color-text-muted)"
            tick={{ fontSize: 11 }}
            label={
              yLabel
                ? {
                    value: yLabel,
                    angle: -90,
                    position: "insideLeft",
                    fill: "var(--color-text-muted)",
                    fontSize: 11,
                  }
                : undefined
            }
          />
          <Tooltip
            contentStyle={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              borderRadius: 8,
              fontSize: 12,
              color: "var(--color-text-body)",
            }}
            labelStyle={{ color: "var(--color-text-heading)", fontWeight: 600 }}
            formatter={(value: number, _name, item) => {
              const capped = (item?.payload as HourlyPoint | undefined)?.is_capped;
              return [
                `${formatUAH(value)} ${capped ? "(капується)" : ""}`,
                unit,
              ];
            }}
          />
          {cap !== null && cap !== undefined && cap > 0 && (
            <ReferenceLine
              y={cap}
              stroke="var(--color-alert)"
              strokeDasharray="6 4"
              label={{
                value: `Кеп ${formatUAH(cap)}`,
                fill: "var(--color-alert)",
                fontSize: 11,
                position: "right",
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke="var(--color-accent)"
            strokeWidth={2}
            dot={<CapDot />}
            activeDot={{ r: 5, fill: "var(--color-accent-deep)" }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

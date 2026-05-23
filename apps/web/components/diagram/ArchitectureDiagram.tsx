"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";

interface DiagramNode {
  id: string;
  label: string;
  children?: string[];
  /** angle in degrees, 0 = right, 90 = down (SVG y is flipped) */
  angle: number;
  href?: string;
  group: "service" | "persona";
}

const HUB = { x: 500, y: 320 };
const RADIUS_UPPER = 220;
const RADIUS_LOWER = 240;

const NODES: DiagramNode[] = [
  // Upper — services (4)
  {
    id: "aux",
    label: "Допоміжні послуги",
    children: ["РВЧ", "БР"],
    angle: -140,
    group: "service",
    href: "/producer",
  },
  {
    id: "trade",
    label: "Торгівля е/е",
    children: ["ДД", "РДН", "ВДР"],
    angle: -110,
    group: "service",
    href: "/producer",
  },
  {
    id: "reg",
    label: "Регуляторні питання",
    children: ["НКРЕКП", "ГП", "Укренерго"],
    angle: -70,
    group: "service",
    href: "/admin",
  },
  {
    id: "ops",
    label: "Технічна справність",
    children: ["Аналітика", "Телеметрія", "ТО"],
    angle: -40,
    group: "service",
    href: "/admin",
  },
  // Lower — personas (4)
  {
    id: "ci",
    label: "Активний споживач",
    angle: 140,
    group: "persona",
    href: "/c-i",
  },
  {
    id: "ses-uze",
    label: "Виробник СЕС + УЗЕ",
    angle: 110,
    group: "persona",
    href: "/producer",
  },
  {
    id: "consumer",
    label: "Споживач",
    angle: 70,
    group: "persona",
    href: "/c-i",
  },
  {
    id: "ves-uze-gpu",
    label: "Виробник ВЕС + УЗЕ + ГПУ",
    angle: 40,
    group: "persona",
    href: "/producer",
  },
];

function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

export function ArchitectureDiagram() {
  const router = useRouter();
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div className="w-full overflow-x-auto scrollbar-thin">
      <svg
        viewBox="0 0 1000 640"
        className="w-full min-w-[640px] h-auto"
        role="img"
        aria-label="Архітектурна діаграма Krytsia VPP"
      >
        {/* Subtle grid */}
        <defs>
          <radialGradient id="hubGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--color-accent-light)" stopOpacity="0.5" />
            <stop offset="100%" stopColor="var(--color-accent)" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Spokes */}
        {NODES.map((n) => {
          const radius = n.group === "service" ? RADIUS_UPPER : RADIUS_LOWER;
          const p = polar(HUB.x, HUB.y, radius, n.angle);
          const active = hovered === n.id;
          return (
            <motion.line
              key={`spoke-${n.id}`}
              x1={HUB.x}
              y1={HUB.y}
              x2={p.x}
              y2={p.y}
              stroke={
                active ? "var(--color-accent-deep)" : "var(--color-border-strong)"
              }
              strokeWidth={active ? 2.5 : 1.5}
              strokeDasharray={active ? "0" : "4 4"}
              initial={false}
              animate={{
                strokeWidth: active ? 2.5 : 1.5,
                opacity: active ? 1 : 0.7,
              }}
              transition={{ duration: 0.2 }}
            />
          );
        })}

        {/* Hub glow */}
        <circle cx={HUB.x} cy={HUB.y} r={120} fill="url(#hubGlow)" />

        {/* Hub */}
        <g>
          <circle
            cx={HUB.x}
            cy={HUB.y}
            r={84}
            fill="var(--color-accent-deep)"
            stroke="var(--color-accent-light)"
            strokeWidth={3}
          />
          <text
            x={HUB.x}
            y={HUB.y - 6}
            textAnchor="middle"
            fontSize={22}
            fontWeight={800}
            fill="var(--color-text-inverse)"
            letterSpacing="0.06em"
          >
            KRYTSIA
          </text>
          <text
            x={HUB.x}
            y={HUB.y + 22}
            textAnchor="middle"
            fontSize={14}
            fontWeight={600}
            fill="var(--color-accent-light)"
          >
            VPP · EMS
          </text>
        </g>

        {/* Nodes */}
        {NODES.map((n) => {
          const radius = n.group === "service" ? RADIUS_UPPER : RADIUS_LOWER;
          const p = polar(HUB.x, HUB.y, radius, n.angle);
          const active = hovered === n.id;
          const isService = n.group === "service";
          return (
            <g
              key={n.id}
              transform={`translate(${p.x},${p.y})`}
              onMouseEnter={() => setHovered(n.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => n.href && router.push(n.href)}
              style={{ cursor: n.href ? "pointer" : "default" }}
            >
              <motion.rect
                x={-90}
                y={isService ? -44 : -22}
                width={180}
                height={isService ? 64 : 44}
                rx={10}
                fill={
                  active ? "var(--color-accent)" : "var(--color-bg-card)"
                }
                stroke={
                  active ? "var(--color-accent-deep)" : "var(--color-border-strong)"
                }
                strokeWidth={active ? 2 : 1.5}
                animate={{ scale: active ? 1.04 : 1 }}
                transition={{ duration: 0.15 }}
              />
              <text
                x={0}
                y={isService ? -22 : 4}
                textAnchor="middle"
                fontSize={13}
                fontWeight={700}
                fill={
                  active ? "var(--color-text-inverse)" : "var(--color-text-heading)"
                }
              >
                {n.label}
              </text>
              {n.children && (
                <text
                  x={0}
                  y={-2}
                  textAnchor="middle"
                  fontSize={11}
                  fill={
                    active ? "var(--color-text-inverse)" : "var(--color-text-muted)"
                  }
                >
                  {n.children.join(" · ")}
                </text>
              )}
            </g>
          );
        })}

        {/* Section labels */}
        <text
          x={HUB.x}
          y={64}
          textAnchor="middle"
          fontSize={12}
          fontWeight={600}
          fill="var(--color-text-muted)"
          letterSpacing={2}
        >
          СЕРВІСИ ТА РИНКИ
        </text>
        <text
          x={HUB.x}
          y={612}
          textAnchor="middle"
          fontSize={12}
          fontWeight={600}
          fill="var(--color-text-muted)"
          letterSpacing={2}
        >
          УЧАСНИКИ
        </text>
      </svg>

      <p
        aria-live="polite"
        className={clsx(
          "mt-2 text-center text-sm",
          hovered ? "text-accent-deep" : "text-text-muted",
        )}
      >
        {hovered
          ? "Натисніть, щоб перейти у відповідний кабінет."
          : "Наведіть курсор на вузол, щоб побачити зв'язок з центром."}
      </p>
    </div>
  );
}

"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import clsx from "clsx";
import { ArrowRight } from "lucide-react";

export interface ScenarioCardProps {
  title: string;
  description: ReactNode;
  href?: string;
  onClick?: () => void;
  cta?: string;
  icon?: ReactNode;
  tone?: "default" | "accent";
}

export function ScenarioCard({
  title,
  description,
  href,
  onClick,
  cta = "Перейти",
  icon,
  tone = "default",
}: ScenarioCardProps) {
  const body = (
    <div
      className={clsx(
        "group rounded-xl border p-5 transition-all h-full flex flex-col gap-3",
        tone === "accent"
          ? "border-accent bg-accent-subtle hover:bg-accent-subtle/80"
          : "border-border bg-bg-card hover:border-accent hover:shadow-elevated",
      )}
    >
      {icon && (
        <span
          className={clsx(
            "inline-flex items-center justify-center w-10 h-10 rounded-lg",
            tone === "accent"
              ? "bg-accent text-text-inverse"
              : "bg-accent-subtle text-accent-deep",
          )}
        >
          {icon}
        </span>
      )}
      <h3 className="text-lg font-semibold text-text-heading">{title}</h3>
      <div className="text-sm text-text-muted flex-1">{description}</div>
      <span
        className={clsx(
          "inline-flex items-center gap-1.5 text-sm font-medium",
          tone === "accent" ? "text-accent-deep" : "text-accent",
        )}
      >
        {cta}
        <ArrowRight
          size={14}
          className="transition-transform group-hover:translate-x-0.5"
        />
      </span>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block h-full">
        {body}
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className="block h-full text-left w-full"
    >
      {body}
    </button>
  );
}

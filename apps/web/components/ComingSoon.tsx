import Link from "next/link";
import { Clock, ArrowLeft } from "lucide-react";

export function ComingSoon({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <span className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent-subtle text-accent-deep mb-4">
        <Clock size={28} />
      </span>
      <h1 className="text-2xl sm:text-3xl font-bold text-text-heading">
        {title}
      </h1>
      <p className="mt-3 text-base text-text-muted max-w-xl">{description}</p>
      <Link
        href="/"
        className="mt-6 inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-border bg-bg-card hover:border-accent transition-colors text-sm"
      >
        <ArrowLeft size={14} />
        На головну
      </Link>
    </div>
  );
}

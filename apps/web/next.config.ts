import type { NextConfig } from "next";

/**
 * NOTE: Intentionally do NOT install @vercel/analytics.
 * See memory `project_vercel_analytics_next16_bug.md` —
 * @vercel/analytics@2.x conflicts with Vercel's modifyConfig on Next 16.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_BASE:
      process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000",
  },
};

export default nextConfig;

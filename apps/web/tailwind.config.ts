import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: {
          page: "var(--color-bg-page)",
          card: "var(--color-bg-card)",
          elevated: "var(--color-bg-elevated)",
          subtle: "var(--color-bg-subtle)",
        },
        text: {
          body: "var(--color-text-body)",
          heading: "var(--color-text-heading)",
          muted: "var(--color-text-muted)",
          inverse: "var(--color-text-inverse)",
        },
        border: {
          DEFAULT: "var(--color-border)",
          strong: "var(--color-border-strong)",
        },
        accent: {
          DEFAULT: "var(--color-accent)",
          deep: "var(--color-accent-deep)",
          light: "var(--color-accent-light)",
          subtle: "var(--color-accent-subtle)",
        },
        success: "var(--color-success)",
        warning: "var(--color-warning)",
        alert: "var(--color-alert)",
        info: "var(--color-info)",
      },
      backgroundImage: {
        "gradient-page": "var(--gradient-page)",
        "gradient-hero": "var(--gradient-hero)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(var(--color-shadow) / 0.08), 0 1px 2px rgba(var(--color-shadow) / 0.06)",
        elevated: "0 8px 24px rgba(var(--color-shadow) / 0.10), 0 2px 6px rgba(var(--color-shadow) / 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;

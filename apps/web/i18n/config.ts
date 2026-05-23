export const locales = ["en", "uk", "pl", "ru"] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

export const LOCALE_COOKIE = "krytsia-locale";

export const LOCALE_META: Record<
  Locale,
  { label: string; nativeLabel: string; flag: string }
> = {
  en: { label: "English", nativeLabel: "English", flag: "🇬🇧" },
  uk: { label: "Ukrainian", nativeLabel: "Українська", flag: "🇺🇦" },
  pl: { label: "Polish", nativeLabel: "Polski", flag: "🇵🇱" },
  ru: { label: "Russian", nativeLabel: "Русский", flag: "🇷🇺" },
};

export function isLocale(value: string | undefined): value is Locale {
  return !!value && (locales as readonly string[]).includes(value);
}

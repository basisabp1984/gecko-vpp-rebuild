import { getRequestConfig } from "next-intl/server";
import { cookies, headers } from "next/headers";
import {
  defaultLocale,
  isLocale,
  LOCALE_COOKIE,
  locales,
  type Locale,
} from "./config";

function pickFromAcceptLanguage(header: string | null): Locale | null {
  if (!header) return null;
  // Format: "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7"
  const ranked = header
    .split(",")
    .map((part) => {
      const [tag, qStr] = part.trim().split(";q=");
      const q = qStr ? parseFloat(qStr) : 1;
      const base = tag.split("-")[0]?.toLowerCase();
      return { base, q };
    })
    .filter((p) => p.base)
    .sort((a, b) => b.q - a.q);
  for (const { base } of ranked) {
    if (base && (locales as readonly string[]).includes(base)) {
      return base as Locale;
    }
  }
  return null;
}

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const cookieLocale = cookieStore.get(LOCALE_COOKIE)?.value;

  let locale: Locale = defaultLocale;
  if (isLocale(cookieLocale)) {
    locale = cookieLocale;
  } else {
    const headerList = await headers();
    const fromHeader = pickFromAcceptLanguage(
      headerList.get("accept-language"),
    );
    if (fromHeader) locale = fromHeader;
  }

  const messages = (await import(`../messages/${locale}.json`)).default;

  return {
    locale,
    messages,
  };
});

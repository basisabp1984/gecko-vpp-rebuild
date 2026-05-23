import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { AppShell } from "@/components/AppShell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin", "cyrillic"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "GECKO VPP — віртуальна електростанція",
  description:
    "Робимо складну енергетику керованою. Для бізнесу. Для виробників. Для ринку.",
};

// Inline script to apply theme BEFORE hydration, avoiding FOUC.
const themeBootstrap = `
(function() {
  try {
    var raw = localStorage.getItem('gecko-theme');
    if (!raw) return;
    var parsed = JSON.parse(raw);
    var theme = parsed && parsed.state && parsed.state.theme;
    if (theme === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="uk"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
      </head>
      <body className="min-h-full flex flex-col bg-bg-page text-text-body">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}

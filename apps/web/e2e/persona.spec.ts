import { test, expect } from "@playwright/test";

test.describe("persona navigation — producer cabinet", () => {
  test("primary CTA navigates to /producer and renders the cabinet skeleton", async ({
    page,
  }) => {
    await page.goto("/");

    await Promise.all([
      page.waitForURL(/\/producer\/?$/, { timeout: 15_000 }),
      page.getByRole("link", { name: /Try a cabinet/i }).first().click(),
    ]);

    // Cabinet header is hard-coded Ukrainian per the product brief
    // (the rest of the cabinet is translated, but H1 stays UA — it's the
    // "Кабінет виробника" / Producer cabinet brand line).
    await expect(
      page.getByRole("heading", { name: /Кабінет виробника/ }),
    ).toBeVisible();

    // KPI tiles render even when the API is down (they show "—" placeholder).
    // Just assert at least one of the labels is on the page.
    await expect(page.getByText(/Грн зароблено/)).toBeVisible();
  });

  test("persona AI helper card is prominent on the producer cabinet", async ({
    page,
  }) => {
    await page.goto("/producer");

    // PersonaAIHelper card has the "AI helper" badge from messages.en.
    await expect(page.getByText(/AI helper/i)).toBeVisible();
  });
});

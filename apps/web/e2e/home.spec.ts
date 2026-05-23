import { test, expect } from "@playwright/test";

test.describe("home page — hero + cinematic landing", () => {
  test("renders eyebrow, headline and both CTAs", async ({ page }) => {
    await page.goto("/");

    // Hero section is a landmark with aria-label="Krytsia hero".
    const hero = page.getByRole("region", { name: "Krytsia hero" });
    await expect(hero).toBeVisible();

    // Headline copy from messages/en.json.
    await expect(
      page.getByText("We make complex energy", { exact: false }),
    ).toBeVisible();
    await expect(
      page.getByText("manageable", { exact: false }),
    ).toBeVisible();

    // Primary CTA — goes to the producer cabinet.
    await expect(
      page.getByRole("link", { name: /Try a cabinet/i }),
    ).toBeVisible();
  });

  test("shows three persona scenario cards", async ({ page }) => {
    await page.goto("/");

    await expect(
      page.getByRole("heading", { name: /Pick your scenario/i }),
    ).toBeVisible();

    await expect(page.getByText(/I'm a producer/i)).toBeVisible();
    await expect(page.getByText(/I'm a business/i)).toBeVisible();
    await expect(page.getByText(/I'm a storage owner/i)).toBeVisible();
  });
});

import { test, expect } from "@playwright/test";

test.describe("main navigation — developer is hidden from the header", () => {
  test("header (main nav) contains no link to /developer", async ({ page }) => {
    await page.goto("/");

    const header = page.locator("header").first();
    await expect(header).toBeVisible();

    // /developer must not be reachable from the header nav.
    // (It is reachable from the footer — that's intentional, the developer
    // surface is for the ~5% of visitors who actually need the API.)
    const headerDeveloperLinks = header.locator('a[href^="/developer"]');
    await expect(headerDeveloperLinks).toHaveCount(0);
  });

  test("footer still surfaces the developer portal link", async ({ page }) => {
    await page.goto("/");

    const footer = page.locator("footer").first();
    await expect(footer).toBeVisible();

    const footerDeveloperLink = footer.locator('a[href^="/developer"]');
    await expect(footerDeveloperLink).toHaveCount(1);
  });
});

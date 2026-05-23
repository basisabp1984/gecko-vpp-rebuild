import { test, expect } from "@playwright/test";

test.describe("LocaleSwitcher — cookie-based i18n", () => {
  test("switching to Ukrainian re-renders the headline in UA", async ({
    page,
    context,
  }) => {
    await page.goto("/");

    // Default locale is en-US (Playwright default), so English headline
    // is present.
    await expect(
      page.getByText("We make complex energy", { exact: false }),
    ).toBeVisible();

    // Open switcher (Globe button with aria-label="Language").
    const switcher = page.getByRole("button", { name: /^Language$/i });
    await switcher.click();

    // Click the Ukrainian option (listbox option labelled "Українська").
    await page.getByRole("option", { name: /Українська/i }).click();

    // Cookie was set; router.refresh() re-fetches the layout in UA.
    await expect(
      page.getByText(/Робимо складну енергетику/),
    ).toBeVisible({ timeout: 10_000 });

    // Cookie should be persisted to "uk".
    const cookies = await context.cookies();
    const localeCookie = cookies.find((c) => c.name === "krytsia-locale");
    expect(localeCookie?.value).toBe("uk");
  });
});

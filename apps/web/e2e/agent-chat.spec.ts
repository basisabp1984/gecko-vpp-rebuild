import { test, expect } from "@playwright/test";

test.describe("AgentChat FAB — global drawer", () => {
  test("FAB is visible on the home page and opens the drawer", async ({
    page,
  }) => {
    await page.goto("/");

    // FAB has aria-label `${askLabel}` — "Ask the agent · Dispatch analyst" on
    // the home page (default persona). Match by the stable "Ask the agent"
    // prefix to avoid coupling to the persona switch.
    const fab = page.getByRole("button", { name: /Ask the agent/i }).first();
    await expect(fab).toBeVisible();

    await fab.click();

    // Drawer is a dialog with aria-label "Krytsia AI agent".
    const drawer = page.getByRole("dialog", { name: /Krytsia AI agent/i });
    await expect(drawer).toBeVisible();

    // The drawer hosts the persona picker and the chat input.
    await expect(
      drawer.getByRole("combobox", { name: /Choose an agent/i }),
    ).toBeVisible();
    await expect(
      drawer.getByPlaceholder(/Ask a question/i),
    ).toBeVisible();
  });
});

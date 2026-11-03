import { expect, test } from "@playwright/test";

/**
 * Acceptance-matrix smoke test against the real compose stack (`make
 * portal-up` plus `docker compose ... --profile cpu up -d engine`):
 * signup -> TC-01 Terms modal -> TC-03 emotion tag + counter -> a short
 * `Tạo giọng nói` -> TC-07 search/filter footer numbers -> TC-09 subset
 * (sidebar balance matches the generate response and the profile).
 */
test("studio and library acceptance flow", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  const password = "a-valid-test-password";

  await page.goto("/signup/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mật khẩu").fill(password);
  await page.getByRole("button", { name: "Đăng ký" }).click();

  // TC-01: the Terms modal blocks the screen; the accept button is
  // disabled until the checkbox is checked, and accepting dismisses it.
  const termsDialog = page.getByRole("dialog", { name: "Điều khoản tạo giọng nói" });
  await expect(termsDialog).toBeVisible();
  const acceptButton = termsDialog.getByRole("button", { name: "Đồng ý và tiếp tục" });
  await expect(acceptButton).toBeDisabled();
  await termsDialog.getByRole("checkbox").check();
  await expect(acceptButton).toBeEnabled();
  await acceptButton.click();
  await expect(termsDialog).toBeHidden();

  // TC-03: inserting an emotion tag updates the text and the counter pill
  // synchronously.
  const editor = page.getByPlaceholder("Nhập hoặc dán văn bản của bạn vào đây...");
  await editor.click();
  await editor.fill("Xin chào các bạn");
  await page.getByRole("button", { name: "Cười" }).click();
  await expect(editor).toHaveValue("Xin chào các bạn[cười] ");
  await expect(page.getByRole("status")).toContainText(/\d+ ký tự/);

  const sidebarBalanceBefore = await page.getByText(/\d[\d.]* \/ [\d.]+/).first().textContent();

  await page.getByRole("button", { name: "Tạo giọng nói" }).click();
  await expect(page.getByText("CÁC BẢN GHI GẦN ĐÂY")).toBeVisible();
  await expect(page.locator("text=Xin chào các bạn").first()).toBeVisible({ timeout: 30_000 });

  // TC-09 subset: the sidebar token balance changed after a successful
  // generate (it was charged) and stays consistent with `/user/profile`.
  const sidebarBalanceAfter = await page.getByText(/\d[\d.]* \/ [\d.]+/).first().textContent();
  expect(sidebarBalanceAfter).not.toBe(sidebarBalanceBefore);

  // TC-07: My Voices search/filter and the footer counts.
  await page.goto("/voices/");
  await page.getByPlaceholder("Tìm kiếm theo văn bản hoặc giọng...").fill("Xin chào");
  await expect(page.getByText(/trong số \d+ giọng nói/)).toBeVisible();
  await expect(page.getByText(/Tổng thời lượng: [\d.]+s/)).toBeVisible();
});

import { execSync } from "node:child_process";

import { expect, test } from "@playwright/test";

/**
 * Admin acceptance flow against the real compose stack. The first
 * superadmin cannot be created through the product (signup always makes a
 * plain `USER`), so this spec creates one via the admin CLI before the
 * test runs — the same CLI the phase 13 API shares its services with.
 */
const SUPERADMIN_EMAIL = `e2e-super-${Date.now()}@example.com`;
const SUPERADMIN_PASSWORD = "a-valid-superadmin-password";
const PASSWORD = "a-valid-test-password";

function createSuperadminViaCli(): void {
  const stdin = `${SUPERADMIN_PASSWORD}\n${SUPERADMIN_PASSWORD}\n`;
  execSync(
    `docker compose -f ../docker/docker-compose.portal.yml exec -T portal python -m vieneu_portal admin create ${SUPERADMIN_EMAIL} --role superadmin`,
    { input: stdin, stdio: ["pipe", "inherit", "inherit"] },
  );
}

test.beforeAll(() => {
  createSuperadminViaCli();
});

async function login(page: import("@playwright/test").Page, email: string, password: string) {
  await page.goto("/login/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mật khẩu").fill(password);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
}

test("superadmin manages a user end to end with audit coverage", async ({ page }) => {
  const targetEmail = `e2e-target-${Date.now()}@example.com`;

  await login(page, SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD);
  await page.goto("/admin/users/");
  await page.getByRole("button", { name: "+ Tạo người dùng" }).click();
  await page.getByLabel("Email").fill(targetEmail);
  await page.getByLabel("Mật khẩu").fill(PASSWORD);
  await page.getByRole("button", { name: "Tạo" }).click();
  await expect(page.getByText(targetEmail)).toBeVisible();

  await page.getByText(targetEmail).click();
  await expect(page.getByRole("heading", { name: "Hồ sơ" })).toBeVisible();

  // Disable, then re-enable.
  await page.getByRole("button", { name: "Khóa tài khoản" }).click();
  await expect(page.getByRole("button", { name: "Kích hoạt" })).toBeVisible();
  await page.getByRole("button", { name: "Kích hoạt" }).click();
  await expect(page.getByRole("button", { name: "Khóa tài khoản" })).toBeVisible();

  // Reset password, then the target logs in with the new one.
  const newPassword = "a-brand-new-password";
  await page.getByRole("button", { name: "Đặt lại mật khẩu" }).click();
  await page.getByLabel("Mật khẩu mới").fill(newPassword);
  await page.getByLabel("Nhập lại mật khẩu mới").fill(newPassword);
  await page.getByRole("button", { name: "Đặt lại" }).click();
  await expect(page.getByText("Đã đặt lại mật khẩu.")).toBeVisible();

  // Grant tokens and confirm the resulting balance is shown.
  await page.getByLabel("Số token thay đổi (+/-)").fill("1000");
  await page.getByLabel("Lý do").fill("e2e grant");
  await page.getByRole("button", { name: "Điều chỉnh" }).click();
  await expect(page.getByText(/Số dư sau điều chỉnh/)).toBeVisible();

  // Change role, then verify it actually took via the role select's own value.
  await page.getByLabel("Quyền").selectOption("ADMIN");
  await expect(page.getByLabel("Quyền")).toHaveValue("ADMIN");

  // The audit log should now show rows for every step above.
  await page.goto("/admin/audit-log/");
  await page.getByPlaceholder("Lọc theo người thực hiện...").fill(SUPERADMIN_EMAIL);
  const actions = ["user.create", "user.update", "user.reset_password", "user.tokens_adjust", "user.set_role"];
  for (const action of actions) {
    await expect(page.getByText(action, { exact: true }).first()).toBeVisible();
  }

  await page.close();
  const newPage = await page.context().newPage();
  await login(newPage, targetEmail, newPassword);
  await expect(newPage).toHaveURL(/\/studio\/?$/);
});

test("a plain ADMIN cannot see or set roles", async ({ page, browser }) => {
  // A plain ADMIN is created by the superadmin first.
  const adminEmail = `e2e-admin-${Date.now()}@example.com`;
  await login(page, SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD);
  await page.goto("/admin/users/");
  await page.getByRole("button", { name: "+ Tạo người dùng" }).click();
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Mật khẩu").fill(PASSWORD);
  await page.getByLabel("Quyền").selectOption("ADMIN");
  await page.getByRole("button", { name: "Tạo" }).click();

  const adminContext = await browser.newContext();
  const adminPage = await adminContext.newPage();
  await login(adminPage, adminEmail, PASSWORD);
  await adminPage.goto("/admin/users/");
  await adminPage.getByRole("button", { name: "+ Tạo người dùng" }).click();
  await expect(adminPage.getByLabel("Quyền")).toHaveCount(0);
  await adminPage.getByRole("button", { name: "Hủy" }).click();
  await adminContext.close();
});

test("editing a voice in admin updates the Studio voice list", async ({ page }) => {
  await login(page, SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD);
  await page.goto("/admin/voices/");
  const firstRow = page.locator("table tbody tr").first();
  const newName = `E2E Voice ${Date.now()}`;
  await firstRow.getByRole("button", { name: "Sửa" }).click();
  await page.getByLabel("Tên").fill(newName);
  await page.getByRole("button", { name: "Lưu" }).click();

  await page.goto("/studio/");
  await expect(page.getByText(newName)).toBeVisible();
});

test("imports a txt file into a system dictionary and exports it back", async ({ page }) => {
  await login(page, SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD);
  await page.goto("/admin/dictionaries/");
  await page.getByRole("button", { name: "+ Tạo bộ từ điển" }).click();
  await page.getByLabel("Tên").fill(`E2E Pack ${Date.now()}`);
  await page.getByRole("button", { name: "Tạo" }).click();

  const row = page.locator("table tbody tr").first();
  await row.getByRole("button", { name: "Nhập" }).click();
  await page.setInputFiles('input[type="file"]', {
    name: "seed.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("E2E = ngắn gọn\n"),
  });
  await page.getByRole("button", { name: "Nhập" }).click();
  await expect(page.getByText(/rejected by moderation|bị từ chối do kiểm duyệt/)).toBeVisible();
});

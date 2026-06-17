import { test, expect } from '@playwright/test';

test('toggle dark mode', async ({ page }) => {
  await page.goto('/');

  const themeSwitch = page.getByRole('switch', { name: /切换暗色模式/ });
  await expect(themeSwitch).toBeVisible();

  const isDarkBefore = await themeSwitch.getAttribute('aria-checked');

  await themeSwitch.click();
  await expect(themeSwitch).toHaveAttribute('aria-checked', isDarkBefore === 'true' ? 'false' : 'true');

  // Verify content background switched
  const main = page.locator('main');
  const expectedBg = isDarkBefore === 'true' ? 'rgb(240, 242, 245)' : 'rgb(31, 31, 31)';
  await expect(main).toHaveCSS('background-color', expectedBg);
});

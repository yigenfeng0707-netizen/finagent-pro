import { test, expect } from '@playwright/test';

test('homepage loads and navigation works', async ({ page }) => {
  await page.goto('/');

  await expect(page).toHaveTitle(/FinAgent Pro/);
  await expect(page.getByRole('heading', { name: '投资仪表盘' })).toBeVisible();

  const menuItems = ['港股行情', 'Agent对话', '数字员工工作台', '组合分析', '风险评估', '系统设置'];
  for (const label of menuItems) {
    await page.getByRole('menuitem', { name: label }).click();
    await expect(page.locator('h2')).toContainText(label);
  }
});

import { test, expect } from '@playwright/test';

test('agent chat flow with mocked backend', async ({ page }) => {
  await page.route('**/api/chat', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        type: 'general',
        session_id: 'e2e-test-session',
        message: '您好！我是FinAgent Pro智能投顾助手。请告诉我您想分析哪只港股？',
      }),
    });
  });

  await page.goto('/agents');

  const input = page.getByPlaceholder('输入消息，如：分析腾讯、帮我看看美团...');
  await expect(input).toBeVisible();

  await input.fill('分析腾讯');
  await page.getByRole('button', { name: '发送' }).click();

  await expect(page.getByText('分析腾讯')).toBeVisible();
  await expect(page.getByText('您好！我是FinAgent Pro智能投顾助手')).toBeVisible();
});

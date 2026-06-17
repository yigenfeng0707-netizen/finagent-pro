import { defineConfig, devices } from '@playwright/test';
import fs from 'fs';

const SYSTEM_CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const hasSystemChrome = fs.existsSync(SYSTEM_CHROME);

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: hasSystemChrome
        ? {
            // 本地直接使用已安装的 Google Chrome，避免下载 Chromium
            browserName: 'chromium',
            channel: 'chrome' as const,
            viewport: { width: 1280, height: 720 },
            launchOptions: {
              executablePath: SYSTEM_CHROME,
            },
          }
        : { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run preview',
    url: 'http://localhost:4173',
    reuseExistingServer: true,
    timeout: 120 * 1000,
  },
});

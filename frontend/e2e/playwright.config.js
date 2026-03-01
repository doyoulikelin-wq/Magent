import { defineConfig } from '@playwright/test';
export default defineConfig({
    testDir: './tests',
    use: {
        baseURL: 'http://localhost:5173',
        headless: true,
    },
    webServer: {
        command: 'npm run dev',
        port: 5173,
        reuseExistingServer: true,
        timeout: 120_000,
    },
});

import { expect, test } from '@playwright/test';
test('landing renders auth panel', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('MetaboDash')).toBeVisible();
    await expect(page.getByRole('button', { name: '登录' })).toBeVisible();
});

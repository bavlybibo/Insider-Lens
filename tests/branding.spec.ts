import {test,expect} from '@playwright/test';
for(const route of ['/', '/?region=canada&view=retention'])test(`Insider Lens identity and immutable evidence ${route}`,async({page})=>{
 await page.goto(route);await expect(page).toHaveTitle('Insider Lens · Evidence before inference');
 await expect(page.getByRole('link',{name:'Insider Lens home',exact:true})).toBeVisible();
 await expect(page.locator('.brand')).toContainText('Insider Lens');
 expect(await page.locator('link[rel="icon"]').getAttribute('href')).toBe('/identity/insider-lens.svg');
 if(route!=='/')await expect(page.locator('[data-retention-ready=true]')).toBeVisible();
 else await expect(page.getByTestId('export')).toBeEnabled();
 const pending=page.waitForEvent('download');await (route==='/'?page.getByTestId('export'):page.getByRole('button',{name:'Export Evidence Retention keys CSV',exact:true})).click();
 const d=await pending;expect(d.suggestedFilename()).toMatch(/^insider-lens-/);expect(d.suggestedFilename()).not.toMatch(/^emberguard-/);
});

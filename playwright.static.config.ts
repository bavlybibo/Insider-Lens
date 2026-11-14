import {defineConfig} from '@playwright/test';
// No development server, cookies, service workers or authenticated storage state.
// Use an explicitly selected built preview or verified production origin.
export default defineConfig({testDir:'./tests',timeout:60_000,workers:1,retries:0,
 testMatch:/cloudflare-static\.spec\.ts|desktop-judge\.spec\.ts|phase(6|7|8|9|10|12)\.spec\.ts|canada-product\.spec\.ts|branding\.spec\.ts/,
 grepInvert:/mobile|390|320/,
 use:{baseURL:process.env.INSIDER_LENS_TEST_ORIGIN??'http://127.0.0.1:5187',viewport:{width:1440,height:900},serviceWorkers:'block',launchOptions:{args:['--enable-unsafe-swiftshader']},screenshot:'only-on-failure',trace:'retain-on-failure'},
 reporter:[['list'],['json',{outputFile:process.env.INSIDER_LENS_BROWSER_REPORT??'reports/cloudflare/static-browser.json'}]]
});

import {defineConfig} from '@playwright/test';
import config from './playwright.static.config';
export default defineConfig({...config,testMatch:/pages-route\.spec\.ts/,
 use:{...config.use,baseURL:process.env.INSIDER_LENS_TEST_ORIGIN??'https://insider-lens.pages.dev'},
 reporter:[['list'],['json',{outputFile:process.env.INSIDER_LENS_BROWSER_REPORT??'reports/pages-repair/browser.json'}]]});

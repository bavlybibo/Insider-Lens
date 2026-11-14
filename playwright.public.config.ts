import {defineConfig} from '@playwright/test';
import full from './playwright.config';
// One unpublished acquisition-path-bearing Phase2 audit receipt is intentionally absent.
// The unchanged complete workspace suite still includes this contract test.
export default defineConfig({...full,
 grepInvert:/staged historical progress is hash-bound to its audit and never a released month/,
 reporter:[['list']],
 webServer:{...full.webServer as object,command:'npm run dev',url:'http://127.0.0.1:5173',reuseExistingServer:true}
});

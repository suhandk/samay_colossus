import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'e2e',testIgnore:'integration.spec.ts',use:{baseURL:'http://localhost:5173',viewport:{width:360,height:800}},webServer:{command:'npm run dev',url:'http://localhost:5173',reuseExistingServer:true}});

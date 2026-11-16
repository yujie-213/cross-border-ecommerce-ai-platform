import { defineConfig } from '../../../frontend/node_modules/@playwright/test/index.mjs'
export default defineConfig({testDir:'.',testMatch:'product.spec.ts',workers:1,timeout:180000,
  outputDir:'../../../.tmp/b-browser',reporter:[['list'],['json',{outputFile:'../../../.tmp/b-browser-results.json'}]],
  expect:{timeout:12000},use:{actionTimeout:20000,baseURL:process.env.B_BROWSER_URL,browserName:'chromium',channel:'msedge',viewport:{width:1440,height:1000},trace:'off',screenshot:'only-on-failure',video:'off'}})

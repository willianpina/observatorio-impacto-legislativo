import {defineConfig} from '@playwright/test';

// Usado apenas pela conferência opt-in das mutações de helpers e proxy.
export default defineConfig({
  testDir:'./tests',testMatch:['proxy.spec.ts','o3r.spec.ts','o3c.spec.ts'],workers:1,fullyParallel:false,
  outputDir:'./test-results/mutation-unit',reporter:'json'
});

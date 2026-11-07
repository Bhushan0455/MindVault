import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    // Reserved live marker. Real-service checks must never be mixed with mocks.
    exclude: ['**/*.live.test.ts', '**/node_modules/**'],
  },
});

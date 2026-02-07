import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
    resolve: {
        alias: {
            '@core': resolve(__dirname, './src/app/core'),
            '@features': resolve(__dirname, './src/app/features'),
            '@shared': resolve(__dirname, './src/app/shared'),
            '@env': resolve(__dirname, './src/environments'),
            '@assets': resolve(__dirname, './src/assets'),
            '@api': resolve(__dirname, './src/app/core/api-generated'),
        },
    },
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: ['./src/test-setup.ts'],
    },
});

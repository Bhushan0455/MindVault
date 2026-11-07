import { defineConfig,loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({mode})=>({ plugins: [react(), tailwindcss()], server:{host:'127.0.0.1',port:5174,strictPort:true,proxy:{'/api':{target:loadEnv(mode,'.','').MINDVAULT_API_PROXY||'http://127.0.0.1:8010',changeOrigin:true}}},preview:{host:'127.0.0.1',port:5174} }));

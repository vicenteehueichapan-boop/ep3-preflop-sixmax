import {defineConfig} from 'vite';
export default defineConfig({server:{proxy:{'/v1':'http://127.0.0.1:8013','/health':'http://127.0.0.1:8013','/docs':'http://127.0.0.1:8013','/openapi.json':'http://127.0.0.1:8013'}}});

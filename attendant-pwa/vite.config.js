import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// WHY host: true — this lets the dev server accept connections from
// outside your laptop, which is required for the `adb reverse` phone-
// testing setup described in the README (camera access needs the
// Android Chrome browser to see the app as "localhost", which adb
// reverse provides without needing a self-signed HTTPS cert).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
});
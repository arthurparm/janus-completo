const env = (import.meta as unknown as { env: Record<string, string | undefined> }).env || {};

export const environment = {
  production: false,
  logging: {
    level: 'debug'
  },
  // Tailscale Funnel Configuration - acesso publico via Tailscale.
  tailscale: {
    enabled: true,
    apiUrl: '/api',
    frontendUrl: 'http://localhost:4300'
  },
  apiUrl: '/api',
  firebase: {
    apiKey: env['JANUS_FIREBASE_API_KEY'] || '',
    authDomain: env['JANUS_FIREBASE_AUTH_DOMAIN'] || '',
    projectId: env['JANUS_FIREBASE_PROJECT_ID'] || '',
    storageBucket: env['JANUS_FIREBASE_STORAGE_BUCKET'] || '',
    messagingSenderId: env['JANUS_FIREBASE_MESSAGING_SENDER_ID'] || '',
    appId: env['JANUS_FIREBASE_APP_ID'] || '',
    measurementId: env['JANUS_FIREBASE_MEASUREMENT_ID'] || '',
    databaseURL: env['JANUS_FIREBASE_DATABASE_URL'] || '',
  }
};

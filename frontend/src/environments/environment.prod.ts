const env = (import.meta as unknown as { env: Record<string, string | undefined> }).env || {};
const tailscaleApiUrl = env['JANUS_TAILSCALE_API_URL'] || '/api';

export const environment = {
  production: true,
  logging: {
    level: 'warn'
  },
  tailscale: {
    enabled: true,
    apiUrl: tailscaleApiUrl,
    frontendUrl: 'http://janus.arthinfo.com.br/'
  },
  apiUrl: tailscaleApiUrl,
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

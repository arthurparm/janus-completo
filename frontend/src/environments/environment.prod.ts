export const environment = {
  production: true,
  logging: {
    level: 'warn'
  },
  tailscale: {
    enabled: true,
    apiUrl: process.env['JANUS_TAILSCALE_API_URL'] || '/api',
    frontendUrl: 'http://janus.arthinfo.com.br/'
  },
  apiUrl: process.env['JANUS_TAILSCALE_API_URL'] || '/api',
  firebase: {
    apiKey: process.env['JANUS_FIREBASE_API_KEY'] || '',
    authDomain: process.env['JANUS_FIREBASE_AUTH_DOMAIN'] || '',
    projectId: process.env['JANUS_FIREBASE_PROJECT_ID'] || '',
    storageBucket: process.env['JANUS_FIREBASE_STORAGE_BUCKET'] || '',
    messagingSenderId: process.env['JANUS_FIREBASE_MESSAGING_SENDER_ID'] || '',
    appId: process.env['JANUS_FIREBASE_APP_ID'] || '',
    measurementId: process.env['JANUS_FIREBASE_MEASUREMENT_ID'] || '',
    databaseURL: process.env['JANUS_FIREBASE_DATABASE_URL'] || '',
  }
};

export const environment = {
  production: false,
  logging: {
    level: 'debug'
  },
  // Tailscale Funnel Configuration - Acesso público via Tailscale
  tailscale: {
    enabled: true, // Tailscale Funnel ativado para acesso público
    apiUrl: '/api', // Usa o proxy local do frontend (funciona via localhost e via Tailscale IP)
    frontendUrl: 'http://localhost:4300'
  },
  // Default API URL - Tailscale Funnel para desenvolvimento
  apiUrl: '/api',
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

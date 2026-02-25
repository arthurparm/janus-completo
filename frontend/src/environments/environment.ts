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
    apiKey: "AIzaSyBbxotMnYYpYsczUteKkx0yWiNFXf8_Y70",
    authDomain: "orbisfracta.firebaseapp.com",
    projectId: "orbisfracta",
    storageBucket: "orbisfracta.firebasestorage.app",
    messagingSenderId: "454482935240",
    appId: "1:454482935240:web:3b5c2e5d13f4c5c7c054fd",
    measurementId: "G-RHL0EHHGFV",
    databaseURL: "https://orbisfracta-default-rtdb.firebaseio.com/"
  }
};

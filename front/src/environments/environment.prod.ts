export const environment = {
  production: true,
  // Tailscale Funnel Configuration - Acesso público via Tailscale
  tailscale: {
    enabled: true, // Tailscale Funnel ativado para produção
    apiUrl: 'https://desktop-hjndm9g.tail041209.ts.net/api', // URL pública Tailscale Funnel
    frontendUrl: 'http://janus.arthinfo.com.br/' // URL do seu site na Locaweb
  },
  // Default API URL - Tailscale Funnel para produção
  apiUrl: 'https://desktop-hjndm9g.tail041209.ts.net/api',
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

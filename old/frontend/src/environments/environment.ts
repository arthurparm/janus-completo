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
  serviceWorker: {
    enabled: false,
  }
};

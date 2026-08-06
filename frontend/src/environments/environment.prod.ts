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
  serviceWorker: {
    enabled: env['JANUS_SERVICE_WORKER_ENABLED'] === 'true',
  }
};

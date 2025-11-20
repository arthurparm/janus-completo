export const environment = {
  production: true,
  supabase: {
    url: 'https://tfunopczianlvppoabmz.supabase.co',
    anonKey: 'sb_publishable_UXz6Oy840f6JQEXiJXe7Lg_LmuosUCA'
  },
  // Tailscale Serve Configuration
  tailscale: {
    enabled: false, // Set to true when using Tailscale Serve
    apiUrl: 'https://janus-backend.tailnet-name.ts.net/api',
    frontendUrl: 'https://janus-frontend.tailnet-name.ts.net'
  },
  // Default API URL (can be overridden by Tailscale)
  apiUrl: 'http://localhost:8000/api'
};
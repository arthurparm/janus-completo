export const environment = {
  production: false,
  supabase: {
    url: 'https://tfunopczianlvppoabmz.supabase.co',
    anonKey: 'sb_publishable_UXz6Oy840f6JQEXiJXe7Lg_LmuosUCA'
  },
  // Tailscale Funnel Configuration - Acesso público via Tailscale
  tailscale: {
    enabled: true, // Tailscale Funnel ativado para acesso público
    apiUrl: 'https://desktop-hjndm9g.tail041209.ts.net/api', // URL pública Tailscale Funnel
    frontendUrl: 'http://localhost:4200'
  },
  // Default API URL - Tailscale Funnel para desenvolvimento
  apiUrl: 'https://desktop-hjndm9g.tail041209.ts.net/api'
};
export const environment = {
  production: true,
  supabase: {
    url: 'https://tfunopczianlvppoabmz.supabase.co',
    anonKey: 'sb_publishable_UXz6Oy840f6JQEXiJXe7Lg_LmuosUCA'
  },
  // Tailscale Funnel Configuration - Acesso público via Tailscale
  tailscale: {
    enabled: true, // Tailscale Funnel ativado para produção
    apiUrl: 'https://desktop-hjndm9g.tail041209.ts.net/api', // URL pública Tailscale Funnel
    frontendUrl: 'http://janus.arthinfo.com.br/' // URL do seu site na Locaweb
  },
  // Default API URL - Tailscale Funnel para produção
  apiUrl: 'https://desktop-hjndm9g.tail041209.ts.net/api'
};
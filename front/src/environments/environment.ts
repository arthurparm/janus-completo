export const environment = {
  production: false,
  supabase: {
    url: 'https://tfunopczianlvppoabmz.supabase.co',
    anonKey: 'sb_publishable_UXz6Oy840f6JQEXiJXe7Lg_LmuosUCA'
  },
  // Tailscale Configuration
  tailscale: {
    enabled: true, // Ativado para usar Tailscale diretamente
    apiUrl: 'http://100.114.164.62:8000/api', // IP Tailscale do backend
    frontendUrl: 'http://localhost:4200'
  },
  // Default API URL (agora usando Tailscale)
  apiUrl: 'http://100.114.164.62:8000/api'
};
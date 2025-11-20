import { Injectable } from '@angular/core'
import { createClient, SupabaseClient } from '@supabase/supabase-js'
import { environment } from '../../../environments/environment'

@Injectable({ providedIn: 'root' })
export class SupabaseService {
  private client?: SupabaseClient
  private ensure() {
    if (!this.client) {
      const url = environment.supabase.url
      const key = environment.supabase.anonKey
      if (!url || !key) {
        throw new Error('Supabase não configurado. Por favor, configure as variáveis no arquivo src/environments/environment.ts')
      }
      this.client = createClient(url, key)
    }
    return this.client
  }
  async signInWithPassword(email: string, password: string) {
    console.log('[SupabaseService] signInWithPassword')
    const c = this.ensure()
    const { data, error } = await c.auth.signInWithPassword({ email, password })
    if (error) throw error
    console.log('[SupabaseService] signInWithPassword:ok')
    return data
  }
  async signInWithProvider(provider: 'google'|'github') {
    console.log('[SupabaseService] signInWithProvider', { provider })
    const c = this.ensure()
    const { data, error } = await c.auth.signInWithOAuth({ provider, options: { skipBrowserRedirect: true } })
    if (error) throw error
    console.log('[SupabaseService] signInWithProvider:ok', { provider })
    return data
  }
  async signInWithProviderRedirect(provider: 'google'|'github') {
    console.log('[SupabaseService] signInWithProviderRedirect', { provider })
    const c = this.ensure()
    const { error } = await c.auth.signInWithOAuth({ provider, options: { redirectTo: `${window.location.origin}/auth/callback` } })
    if (error) throw error
  }
  onAuthStateChange(cb: (event: string) => void) {
    const c = this.ensure()
    return c.auth.onAuthStateChange((evt) => { console.log('[SupabaseService] onAuthStateChange', { evt }); cb(evt) })
  }
  async getSession() {
    console.log('[SupabaseService] getSession')
    const c = this.ensure()
    const { data } = await c.auth.getSession()
    console.log('[SupabaseService] getSession:ok', { hasToken: !!data.session?.access_token })
    return data.session
  }

  async signOut() {
    console.log('[SupabaseService] signOut')
    const c = this.ensure()
    const { error } = await c.auth.signOut()
    if (error) throw error
    console.log('[SupabaseService] signOut:ok')
  }
}
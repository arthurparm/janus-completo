export interface TokenResponse { token: string }
export interface ProductivityLimitUsage { max_per_day: number; used: number; remaining: number }
export interface ProductivityLimitsStatusResponse { user_id: string; limits: Record<string, ProductivityLimitUsage> }
export interface GoogleOAuthStartResponse { authorize_url: string; state: string }
export interface GoogleOAuthCallbackResponse { status: string; state?: string }
export interface GoogleOAuthDisconnectResponse {
  status: 'disconnected' | 'local_disconnected'
  provider_revoked: boolean | null
  retry_required: boolean
  warning?: string | null
}
export interface CalendarEvent { title: string; start_ts: number; end_ts: number; location?: string; notes?: string }
export interface CalendarAddRequest { event: CalendarEvent; index?: boolean }
export interface MailMessage { to: string; subject: string; body: string }
export interface MailSendRequest { message: MailMessage; index?: boolean }
export interface UserStatusResponse { user_id: string; conversations: number; messages: number; approx_in_tokens: number; approx_out_tokens: number; vector_points: number }

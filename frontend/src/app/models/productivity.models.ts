export interface UserRolesResponse { user_id: number; roles: string[] }
export interface TokenResponse { token: string }
export interface ProductivityLimitUsage { max_per_day: number; used: number; remaining: number }
export interface ProductivityLimitsStatusResponse { user_id: string; limits: Record<string, ProductivityLimitUsage> }
export interface GoogleOAuthStartResponse { authorize_url: string }
export interface GoogleOAuthCallbackResponse { status: string; state?: string }
export interface CalendarEvent { title: string; start_ts: number; end_ts: number; location?: string; notes?: string }
export interface CalendarAddRequest { user_id: number; event: CalendarEvent; index?: boolean }
export interface MailMessage { to: string; subject: string; body: string }
export interface MailSendRequest { user_id: number; message: MailMessage; index?: boolean }
export interface UserStatusResponse { user_id: string; conversations: number; messages: number; approx_in_tokens: number; approx_out_tokens: number; vector_points: number }

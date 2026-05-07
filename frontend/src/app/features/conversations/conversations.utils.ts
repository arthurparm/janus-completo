import { ConversationMeta, MemoryItem } from '../../services/backend-api.service'

export function conversationUpdatedAt(conv: ConversationMeta): number {
  const updated = Number(conv.updated_at)
  if (Number.isFinite(updated) && updated > 0) return updated
  const lastTimestamp = Number(conv.last_message?.timestamp)
  if (Number.isFinite(lastTimestamp) && lastTimestamp > 0) return lastTimestamp
  const created = Number(conv.created_at)
  if (Number.isFinite(created) && created > 0) return created
  return 0
}

export function createConversationViewId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function cognitiveStatusText(state: string, reason?: string): string {
  if (state === 'knowledge_wait_estimate') {
    return reason || 'Consulta grounded iniciada; isso pode demorar.'
  }
  if (state === 'studying_codebase') {
    return reason || 'Estudando a base para responder com seguranca; isso pode demorar.'
  }
  if (state === 'study_progress') {
    return reason || 'Estudo em andamento na base local.'
  }
  if (state === 'resuming_answer_generation') {
    return reason || 'Gerando a resposta final a partir do estudo.'
  }
  return `Estado: ${state}${reason ? ` (${reason})` : ''}`
}

export function isConversationMemory(item: MemoryItem, conversationId: string): boolean {
  const metadata = item.metadata || {}
  const target = String(conversationId || '').trim()
  if (!target) return false
  const sessionId = String(metadata.session_id || '').trim()
  const threadId = String(metadata['thread_id'] || '').trim()
  const convoId = String(metadata['conversation_id'] || '').trim()
  const taskId = String(metadata['task_id'] || '').trim()
  const compositeId = String(item.composite_id || '')
  if ([sessionId, threadId, convoId, taskId].some((value) => value === target)) return true
  if (!compositeId) return false
  const compositeTokens = compositeId.split(/[:/|]/g).map((part) => part.trim()).filter(Boolean)
  return compositeTokens.some((part) => part === target)
}

export function coerceDateInputToMs(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value > 10_000_000_000 ? value : value * 1000
  }
  if (typeof value === 'string' && value.trim()) {
    const numeric = Number(value)
    if (Number.isFinite(numeric)) {
      return numeric > 10_000_000_000 ? numeric : numeric * 1000
    }
    const parsed = Date.parse(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

export function extractErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== 'object') return fallback
  const maybe = error as { error?: { detail?: string } }
  const detail = maybe.error?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  return fallback
}

export function sanitizeChatText(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') {
    const cleaned = value
      .replace(/\[\s*object\s+object\s*\]/gi, '')
      .split('')
      .map((ch) => {
        const code = ch.charCodeAt(0)
        const isControl = (code >= 0x00 && code <= 0x08)
          || code === 0x0b
          || code === 0x0c
          || (code >= 0x0e && code <= 0x1f)
          || (code >= 0x7f && code <= 0x9f)
          || code === 0xfffd
        return isControl ? ' ' : ch
      })
      .join('')
      .replace(/\n{3,}/g, '\n\n')
    return cleaned.trim() ? cleaned : ''
  }
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

export function sanitizeStreamingText(value: string): string {
  return String(value || '')
    .replace(/\[\s*object\s+object\s*\]/gi, '')
    .split('')
    .map((ch) => {
      const code = ch.charCodeAt(0)
      const isControl = (code >= 0x00 && code <= 0x08)
        || code === 0x0b
        || code === 0x0c
        || (code >= 0x0e && code <= 0x1f)
        || (code >= 0x7f && code <= 0x9f)
        || code === 0xfffd
      return isControl ? ' ' : ch
    })
    .join('')
    .replace(/\n{3,}/g, '\n\n')
}

export function sanitizeDiagnosticText(value: unknown, fallback = ''): string {
  const raw = sanitizeChatText(value)
  if (!raw) return fallback
  const compact = raw.replace(/\s{2,}/g, ' ').trim()
  if (!compact) return fallback
  if (looksLikeBinaryPayload(compact) || looksLikeStructuredTelemetryNoise(compact)) {
    return fallback || 'Conteudo nao textual omitido'
  }
  return compact
}

function looksLikeBinaryPayload(value: string): boolean {
  if (value.length < 20) return false
  const alphaNumericCount = (value.match(/[A-Za-z0-9\u00C0-\u024F]/g) || []).length
  const symbolRatio = 1 - (alphaNumericCount / value.length)
  return symbolRatio > 0.55
}

function looksLikeStructuredTelemetryNoise(value: string): boolean {
  const lowered = value.toLowerCase()
  const markers = [
    'event_type',
    'agent_role',
    'task_id',
    'metadata',
    'entities_count',
    'relationships_count',
    'memory_consolidated',
  ]
  const hitCount = markers.reduce((acc, marker) => (lowered.includes(marker) ? acc + 1 : acc), 0)
  return hitCount >= 3
}

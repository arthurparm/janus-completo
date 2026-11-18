export interface AdminCodeQaCommandResult {
  enabled: boolean
  question: string | null
}

export function parseAdminCodeQaCommand(
  message: string,
  isAdmin: boolean
): AdminCodeQaCommandResult {
  if (!isAdmin) {
    return { enabled: false, question: null }
  }

  const text = String(message || '').trim()
  const match = text.match(/^\/code\b([\s\S]*)$/i)
  if (!match) {
    return { enabled: false, question: null }
  }

  const question = String(match[1] || '').trim()
  return {
    enabled: true,
    question: question || null
  }
}

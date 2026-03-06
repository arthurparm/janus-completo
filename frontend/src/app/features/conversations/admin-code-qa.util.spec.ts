import { describe, expect, it } from 'vitest'

import { parseAdminCodeQaCommand } from './admin-code-qa.util'

describe('parseAdminCodeQaCommand', () => {
  it('nao ativa code qa para usuario nao admin', () => {
    const result = parseAdminCodeQaCommand('/code me fale de chat', false)
    expect(result).toEqual({ enabled: false, question: null })
  })

  it('nao ativa code qa para pergunta natural no admin', () => {
    const result = parseAdminCodeQaCommand('me fale um arquivo seu', true)
    expect(result).toEqual({ enabled: false, question: null })
  })

  it('ativa code qa quando comando /code e informado', () => {
    const result = parseAdminCodeQaCommand('/code me fale um arquivo seu', true)
    expect(result).toEqual({ enabled: true, question: 'me fale um arquivo seu' })
  })

  it('ativa com question nula quando /code vem sem pergunta', () => {
    const result = parseAdminCodeQaCommand('/code   ', true)
    expect(result).toEqual({ enabled: true, question: null })
  })

  it('suporta comando /code case insensitive', () => {
    const result = parseAdminCodeQaCommand('/CODE arquitetura do chat', true)
    expect(result).toEqual({ enabled: true, question: 'arquitetura do chat' })
  })
})

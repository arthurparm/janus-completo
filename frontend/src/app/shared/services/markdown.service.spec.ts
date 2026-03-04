import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { marked } from 'marked'
import hljs from 'highlight.js'
import { MarkdownService } from './markdown.service'
import { AppLoggerService } from '../../core/services/app-logger.service'

describe('MarkdownService', () => {
  let service: MarkdownService
  const logger = {
    error: vi.fn(),
  }

  const rendererPrototype = marked.Renderer.prototype as { table: (...args: unknown[]) => string }
  const originalTable = rendererPrototype.table

  beforeEach(() => {
    vi.clearAllMocks()
    rendererPrototype.table = originalTable
    service = new MarkdownService(logger as unknown as AppLoggerService)
  })

  afterEach(() => {
    rendererPrototype.table = originalTable
    vi.restoreAllMocks()
  })

  it('renderiza tabela com assinatura atual do marked sem artefatos', () => {
    const markdown = [
      '| Coluna | Valor |',
      '| --- | --- |',
      '| status | ok |',
    ].join('\n')

    const html = service.parse(markdown)

    expect(html).toContain('table-container')
    expect(html).toContain('table table-striped')
    expect(html).not.toContain('[object Object]')
    expect(html).not.toContain('undefined')
  })

  it('faz fallback legado de tabela quando renderer nativo falha', () => {
    rendererPrototype.table = vi.fn(() => {
      throw new Error('forced-renderer-failure')
    })

    const serviceWithFallback = new MarkdownService(logger as unknown as AppLoggerService)
    const tableRenderer = ((marked as unknown as { defaults: { renderer: { table: (...args: unknown[]) => string } } }).defaults.renderer.table)
    const html = tableRenderer('<tr><th>Coluna</th></tr>', '<tr><td>ok</td></tr>')

    expect(html).toContain('table-container')
    expect(html).toContain('table table-striped')
    expect(html).not.toContain('[object Object]')
    expect(html).not.toContain('undefined')
    expect(serviceWithFallback).toBeTruthy()
  })

  it('renderiza fence code normal com lang-label coerente', () => {
    const markdown = ['```typescript', 'const x = 1', '```'].join('\n')
    const html = service.parse(markdown)

    expect(html).toContain('code-block-wrapper')
    expect(html).toContain('lang-label')
    expect(html).toContain('typescript')
    expect(html).not.toContain('[object Object]')
  })

  it('renderiza token object de code sem vazar [object Object]', () => {
    const renderer = (marked as unknown as { defaults: { renderer: { code: (code: unknown, languageHint?: string) => string } } }).defaults.renderer
    const html = renderer.code({ text: 'print("ok")', language: 'python' })

    expect(html).toContain('code-block-wrapper')
    expect(html).toContain('lang-label')
    expect(html).toContain('python')
    expect(html).not.toContain('[object Object]')
  })

  it('degrada para pre/code quando highlight falha', () => {
    vi.spyOn(hljs, 'highlight').mockImplementation(() => {
      throw new Error('highlight-failed')
    })

    const markdown = ['```invalid-lang', 'const y = 2', '```'].join('\n')
    const html = service.parse(markdown)

    expect(html).toContain('<pre><code>')
    expect(html).toContain('const y = 2')
  })
})

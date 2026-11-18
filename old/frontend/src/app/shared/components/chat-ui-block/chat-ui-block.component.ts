import { Component, Input, computed, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import type { ChatUiPayload } from '../../../models'

interface TableData {
  columns: string[]
  rows: Record<string, unknown>[]
}

interface ListData {
  items: unknown[]
}

interface CardData {
  text: string
}

interface ChartSeries {
  name?: string
  values: number[]
}

interface ChartData {
  labels: string[]
  series: ChartSeries[]
}

interface CodeBlockData {
  language?: string
  code: string
}

interface ChartBar {
  label: string
  value: number
  heightPercent: number
}

/** Renderiza o payload estruturado que o LLM embute via `<janus-ui>` nas respostas
 * (ver backend/app/services/chat/message_helpers.py:split_ui). Cada tipo tem um
 * parser defensivo próprio: dado malformado do LLM nunca deve quebrar a tela,
 * só resultar em nada renderizado para aquele componente. */
@Component({
  selector: 'app-chat-ui-block',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './chat-ui-block.component.html',
  styleUrls: ['./chat-ui-block.component.scss']
})
export class ChatUiBlockComponent {
  private readonly _payload = signal<ChatUiPayload | undefined>(undefined)

  @Input()
  set payload(value: ChatUiPayload | undefined) {
    this._payload.set(value)
  }
  get payload(): ChatUiPayload | undefined {
    return this._payload()
  }

  readonly title = computed(() => this._payload()?.title || '')
  readonly description = computed(() => this._payload()?.description || '')
  readonly type = computed(() => this._payload()?.type)

  readonly table = computed<TableData | null>(() => {
    const data = this._payload()?.data
    if (this.type() !== 'table' || !data || typeof data !== 'object') return null
    const columns = Array.isArray(data.columns) ? data.columns.map(String) : null
    const rows = Array.isArray(data.rows) ? data.rows : null
    if (!columns || !rows) return null
    return { columns, rows: rows.filter((r: unknown) => r && typeof r === 'object') }
  })

  readonly list = computed<ListData | null>(() => {
    const data = this._payload()?.data
    if (this.type() !== 'list' || !data || typeof data !== 'object') return null
    const items = Array.isArray(data.items) ? data.items : null
    if (!items) return null
    return { items }
  })

  readonly card = computed<CardData | null>(() => {
    const data = this._payload()?.data
    if (this.type() !== 'card' || !data || typeof data !== 'object') return null
    const text = typeof data.text === 'string' ? data.text : null
    if (!text) return null
    return { text }
  })

  readonly codeBlock = computed<CodeBlockData | null>(() => {
    const data = this._payload()?.data
    if (this.type() !== 'code_block' || !data || typeof data !== 'object') return null
    const code = typeof data.code === 'string' ? data.code : null
    if (code === null) return null
    return { language: typeof data.language === 'string' ? data.language : undefined, code }
  })

  readonly chartBars = computed<ChartBar[] | null>(() => {
    const data = this._payload()?.data as ChartData | undefined
    if (this.type() !== 'chart' || !data || typeof data !== 'object') return null
    const labels = Array.isArray(data.labels) ? data.labels.map(String) : null
    const series = Array.isArray(data.series) ? data.series : null
    const firstSeries = series?.[0]
    const values = Array.isArray(firstSeries?.values) ? firstSeries.values : null
    if (!labels || !values || labels.length === 0 || labels.length !== values.length) return null
    const numericValues = values.map((v) => (typeof v === 'number' && Number.isFinite(v) ? v : 0))
    const max = Math.max(...numericValues, 0)
    if (max <= 0) return null
    return labels.map((label, i) => ({
      label,
      value: numericValues[i],
      heightPercent: Math.max(2, Math.round((numericValues[i] / max) * 100))
    }))
  })

  readonly chartSeriesName = computed<string>(() => {
    const data = this._payload()?.data as ChartData | undefined
    return data?.series?.[0]?.name || ''
  })

  rowValue(row: Record<string, unknown>, column: string): string {
    const value = row[column]
    if (value === null || value === undefined) return ''
    return typeof value === 'object' ? JSON.stringify(value) : String(value)
  }

  itemText(item: unknown): string {
    if (item === null || item === undefined) return ''
    return typeof item === 'object' ? JSON.stringify(item) : String(item)
  }
}

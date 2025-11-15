import {Component, inject} from '@angular/core'
import {JanusApiService, AuditEvent, GraphQuarantineItem} from '../../../services/janus-api.service'
import {NgIf, NgFor, DatePipe} from '@angular/common'
import {FormsModule} from '@angular/forms'

@Component({
  selector: 'app-hitl',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule, DatePipe],
  templateUrl: './hitl.html',
  styleUrls: ['./hitl.scss']
})
export class HitlComponent {
  private api = inject(JanusApiService)
  items: GraphQuarantineItem[] = []
  pageSize = 25
  page = 1
  filters: { type?: string; reason?: string; confidence_ge?: number } = {}
  synonym = { label: '', alias: '', canonical: '' }
  auditUserId = ''
  auditEvents: AuditEvent[] = []
  metrics = { promote: 0, reject: 0, synonym: 0 }
  modal: { visible: boolean; mode: 'promote'|'reject'|null; item: GraphQuarantineItem|null; justification: string } = { visible: false, mode: null, item: null, justification: '' }

  ngOnInit() {
    this.refresh()
  }

  refresh() {
    const limit = this.pageSize
    const offset = (this.page - 1) * this.pageSize
    this.api.listGraphQuarantine(limit, offset, this.filters).subscribe(items => {
      this.items = items
    })
  }

  openPromote(item: GraphQuarantineItem) {
    this.modal = { visible: true, mode: 'promote', item, justification: '' }
  }

  openReject(item: GraphQuarantineItem) {
    this.modal = { visible: true, mode: 'reject', item, justification: '' }
  }

  closeModal() {
    this.modal.visible = false
    this.modal.mode = null
    this.modal.item = null
    this.modal.justification = ''
  }

  confirmPromote() {
    if (!this.modal.item) return
    this.api.promoteQuarantine(this.modal.item.node_id).subscribe(() => {
      this.metrics.promote++
      this.closeModal()
      this.refresh()
    })
  }

  confirmReject() {
    if (!this.modal.item) return
    this.api.rejectQuarantine(this.modal.item.node_id, this.modal.justification).subscribe(() => {
      this.metrics.reject++
      this.closeModal()
      this.refresh()
    })
  }

  submitSynonym() {
    if (!this.synonym.label || !this.synonym.alias || !this.synonym.canonical) return
    this.api.registerSynonym(this.synonym.label, this.synonym.alias, this.synonym.canonical).subscribe(() => {
      this.metrics.synonym++
      this.synonym = { label: '', alias: '', canonical: '' }
    })
  }

  loadAudit() {
    const params: any = { tool: 'hitl', limit: 200 }
    if (this.auditUserId) params.user_id = this.auditUserId
    this.api.listAuditEvents(params).subscribe(res => {
      this.auditEvents = res.events || []
    })
  }

  exportFormat: 'csv'|'json' = 'csv'
  exportFields = 'id,user_id,endpoint,action,tool,status,latency_ms,trace_id,justification,details_json,created_at'
  exportAudit() {
    const fields = this.exportFields.split(',').map(f => f.trim()).filter(Boolean)
    const params: any = { format: this.exportFormat, fields, limit: 1000 }
    this.api.exportAuditEvents(this.exportFormat, params).subscribe(text => {
      const blob = new Blob([text], { type: this.exportFormat === 'csv' ? 'text/csv' : 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit.${this.exportFormat}`
      a.click()
      URL.revokeObjectURL(url)
    })
  }
}

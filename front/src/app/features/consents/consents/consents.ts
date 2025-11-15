import {Component, inject} from '@angular/core'
import {FormsModule} from '@angular/forms'
import {NgIf, NgFor} from '@angular/common'
import {JanusApiService, ConsentItem} from '../../../services/janus-api.service'

@Component({
  selector: 'app-consents',
  standalone: true,
  imports: [FormsModule, NgIf, NgFor],
  templateUrl: './consents.html',
  styleUrls: ['./consents.scss']
})
export class ConsentsComponent {
  private api = inject(JanusApiService)
  userId = 0
  items: ConsentItem[] = []
  ids: number[] = []
  newScope = ''
  newExpires = ''

  loadConsents() {
    if (!this.userId) return
    this.api.listConsents(this.userId).subscribe(res => {
      this.items = res.consents || []
      // IDs não retornam no endpoint atual; placeholder para integração futura
      this.ids = this.items.map(() => 0)
    })
  }

  grant(scope: string, expires?: string) {
    if (!this.userId || !scope) return
    this.api.grantConsent(this.userId, scope, true, expires).subscribe(() => {
      this.loadConsents()
      this.newScope = ''
      this.newExpires = ''
    })
  }

  revoke(id?: number) {
    if (!id) return
    this.api.revokeConsent(id).subscribe(() => this.loadConsents())
  }
}
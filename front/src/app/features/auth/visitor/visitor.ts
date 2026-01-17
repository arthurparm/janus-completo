import { Component, OnInit, inject } from '@angular/core'
import { Router, RouterLink } from '@angular/router'
import { VISITOR_MODE_KEY } from '../../../services/api.config'
import { NgIf } from '@angular/common'

@Component({
  selector: 'app-visitor',
  standalone: true,
  imports: [RouterLink, NgIf],
  templateUrl: './visitor.html',
  styleUrls: ['./visitor.scss']
})
export class VisitorComponent implements OnInit {
  private router = inject(Router)
  error = ''

  ngOnInit(): void {
    try {
      localStorage.setItem(VISITOR_MODE_KEY, '1')
      window.location.assign('/')
    } catch (err) {
      console.error('[Visitor] Failed to set visitor mode:', err)
      this.error = 'Nao foi possivel entrar como visitante.'
    }
  }
}

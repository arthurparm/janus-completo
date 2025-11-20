import {Component, OnInit} from '@angular/core'
import {CommonModule} from '@angular/common'
import {HttpClient} from '@angular/common/http'
import { forkJoin, BehaviorSubject, of, catchError } from 'rxjs'

type GapItem = {
  descricao: string
  data_ausencia: string
  impacto: string
  prioridade: 'alta'|'média'|'baixa'|string
  status: 'pendente'|'em análise'|'descartado'|string
  justificativa: string
  referencias: string
}

type ObsoletoItem = {
  nome: string
  data_descontinuacao: string
  alternativa: string
  motive: string
  impacto_usuarios: string
  plano_migracao: string
}

@Component({
  selector: 'app-janus-gaps',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './janus-gaps.html',
  styleUrl: './janus-gaps.scss'
})
export class JanusGapsComponent implements OnInit {
  gaps: GapItem[] = []
  obsoletos: ObsoletoItem[] = []
  loading$ = new BehaviorSubject<boolean>(true)
  error$ = new BehaviorSubject<string | null>(null)

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    const readCsv = (name: string) => this.http.get(`/${name}`, { responseType: 'text' })
      .pipe(catchError(() => this.http.get(`/assets/${name}`, { responseType: 'text' })), catchError(() => of('')))

    forkJoin({
      gapsCsv: readCsv('janus-gaps.csv'),
      obsCsv: readCsv('janus-obsoleto.csv'),
    }).subscribe({
      next: ({ gapsCsv, obsCsv }) => {
        this.gaps = this.parseCsv<GapItem>(gapsCsv || '', ['descricao','data_ausencia','impacto','prioridade','status','justificativa','referencias'])
        this.obsoletos = this.parseCsv<ObsoletoItem>(obsCsv || '', ['nome','data_descontinuacao','alternativa','motive','impacto_usuarios','plano_migracao'])
        setTimeout(() => { this.loading$.next(false) })
      },
      error: () => { setTimeout(() => { this.loading$.next(false) }) }
    })
  }

  private parseCsv<T extends Record<string, string>>(csv: string, headers: string[]): T[] {
    const lines = csv.split(/\r?\n/).filter(l => l.trim().length)
    if (!lines.length) return []
    const dataLines = lines.slice(1)
    return dataLines.map(line => {
      const parts = line.split(';')
      const item: Record<string, string> = {}
      headers.forEach((h, idx) => { item[h] = (parts[idx] || '').trim() })
      return item as T
    })
  }
}
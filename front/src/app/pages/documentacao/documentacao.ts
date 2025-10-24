import {Component} from '@angular/core'
import {CommonModule} from '@angular/common'
import {RouterModule} from '@angular/router'

@Component({
  selector: 'app-documentacao',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './documentacao.html',
  styleUrl: './documentacao.scss'
})
export class Documentacao {}

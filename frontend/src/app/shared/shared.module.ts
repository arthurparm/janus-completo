import { NgModule } from '@angular/core'
import { CommonModule } from '@angular/common'

// Services
import { UiService } from './services/ui.service'

import { ReactiveFormsModule } from '@angular/forms'

const MATERIAL_MODULES = [
  ReactiveFormsModule
]

@NgModule({
  imports: [
    CommonModule,
    ...MATERIAL_MODULES
  ],
  exports: [
    ...MATERIAL_MODULES
  ],
  providers: [
    UiService
  ]
})
export class SharedModule { }
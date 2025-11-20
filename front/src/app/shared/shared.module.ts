import { NgModule } from '@angular/core'
import { CommonModule } from '@angular/common'

// Services
import { UiService } from './services/ui.service'

// Material Modules
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner'
import { MatButtonModule } from '@angular/material/button'
import { MatIconModule } from '@angular/material/icon'
import { MatDialogModule } from '@angular/material/dialog'
import { MatSnackBarModule } from '@angular/material/snack-bar'
import { ReactiveFormsModule } from '@angular/forms'

const MATERIAL_MODULES = [
  MatProgressSpinnerModule,
  MatButtonModule,
  MatIconModule,
  MatDialogModule,
  MatSnackBarModule,
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
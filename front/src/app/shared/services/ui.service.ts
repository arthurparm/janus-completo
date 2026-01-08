import { Injectable, inject } from '@angular/core'
import { FormGroup } from '@angular/forms'
import { MatSnackBar, MatSnackBarConfig, MatSnackBarRef } from '@angular/material/snack-bar'
import { MatDialog, MatDialogConfig, MatDialogRef } from '@angular/material/dialog'
import { Observable, Subject } from 'rxjs'
import { LoadingDialogComponent } from '../components/loading-dialog/loading-dialog.component'
import { ConfirmDialogComponent } from '../components/confirm-dialog/confirm-dialog.component'

export interface ToastConfig {
  message: string
  action?: string
  duration?: number
  panelClass?: string
  horizontalPosition?: 'start' | 'center' | 'end' | 'left' | 'right'
  verticalPosition?: 'top' | 'bottom'
}

export interface ConfirmDialogData {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmColor?: 'primary' | 'warn' | 'accent'
}

export interface LoadingDialogConfig {
  message?: string
  disableClose?: boolean
}

@Injectable({
  providedIn: 'root'
})
export class UiService {
  private activeToasts: MatSnackBarRef<any>[] = []
  private activeLoadingDialogs: MatDialogRef<LoadingDialogComponent>[] = []

  constructor(
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {}

  // Toast/Snackbar methods
  showToast(config: ToastConfig): void {
    const snackBarConfig: MatSnackBarConfig = {
      duration: config.duration || 3000,
      horizontalPosition: config.horizontalPosition || 'right',
      verticalPosition: config.verticalPosition || 'bottom',
      panelClass: config.panelClass || 'default-toast'
    }

    const toastRef = this.snackBar.open(
      config.message,
      config.action || '',
      snackBarConfig
    )

    this.activeToasts.push(toastRef)
    toastRef.afterDismissed().subscribe(() => {
      const index = this.activeToasts.indexOf(toastRef)
      if (index > -1) {
        this.activeToasts.splice(index, 1)
      }
    })
  }

  showSuccess(message: string, action?: string): void {
    this.showToast({
      message,
      action,
      duration: 4000,
      panelClass: 'success-toast'
    })
  }

  showError(message: string, action?: string): void {
    this.showToast({
      message,
      action,
      duration: 6000,
      panelClass: 'error-toast'
    })
  }

  showWarning(message: string, action?: string): void {
    this.showToast({
      message,
      action,
      duration: 5000,
      panelClass: 'warning-toast'
    })
  }

  showInfo(message: string, action?: string): void {
    this.showToast({
      message,
      action,
      duration: 4000,
      panelClass: 'info-toast'
    })
  }

  // Loading dialog methods
  showLoading(config?: LoadingDialogConfig): MatDialogRef<LoadingDialogComponent> {
    const dialogConfig: MatDialogConfig = {
      disableClose: config?.disableClose !== false,
      data: { message: config?.message || 'Carregando...' },
      panelClass: 'loading-dialog'
    }

    const loadingRef = this.dialog.open(LoadingDialogComponent, dialogConfig)
    this.activeLoadingDialogs.push(loadingRef)
    
    loadingRef.afterClosed().subscribe(() => {
      const index = this.activeLoadingDialogs.indexOf(loadingRef)
      if (index > -1) {
        this.activeLoadingDialogs.splice(index, 1)
      }
    })

    return loadingRef
  }

  hideLoading(): void {
    this.activeLoadingDialogs.forEach(dialog => {
      if (dialog) {
        dialog.close()
      }
    })
    this.activeLoadingDialogs = []
  }

  // Confirmation dialog
  showConfirm(data: ConfirmDialogData): Observable<boolean> {
    const dialogConfig: MatDialogConfig = {
      width: '400px',
      data,
      panelClass: 'confirm-dialog'
    }

    const dialogRef = this.dialog.open(ConfirmDialogComponent, dialogConfig)
    return dialogRef.afterClosed()
  }

  // Utility methods
  dismissAllToasts(): void {
    this.activeToasts.forEach(toast => {
      if (toast) {
        toast.dismiss()
      }
    })
    this.activeToasts = []
  }

  dismissAllDialogs(): void {
    this.dialog.closeAll()
    this.activeLoadingDialogs = []
  }

  // Form validation helpers
  getFormValidationErrors(formGroup: FormGroup): string[] {
    const errors: string[] = []
    
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key)
      const controlErrors = control?.errors
      if (controlErrors != null) {
        Object.keys(controlErrors).forEach(keyError => {
          errors.push(this.getValidationErrorMessage(key, keyError, controlErrors[keyError]))
        })
      }
    })
    
    return errors
  }

  private getValidationErrorMessage(fieldName: string, errorType: string, errorValue: unknown): string {
    const fieldNameMap: Record<string, string> = {
      'email': 'Email',
      'password': 'Senha',
      'name': 'Nome',
      'username': 'Nome de usuário',
      'phone': 'Telefone',
      'cpf': 'CPF',
      'cnpj': 'CNPJ'
    }

    const friendlyFieldName = fieldNameMap[fieldName] || fieldName
    const errObj = errorValue as { requiredLength?: number }

    switch (errorType) {
      case 'required':
        return `${friendlyFieldName} é obrigatório`
      case 'email':
        return `Por favor, insira um email válido`
      case 'minlength':
        return `${friendlyFieldName} deve ter no mínimo ${errObj.requiredLength} caracteres`
      case 'maxlength':
        return `${friendlyFieldName} deve ter no máximo ${errObj.requiredLength} caracteres`
      case 'pattern':
        return `${friendlyFieldName} está em formato inválido`
      case 'mustMatch':
        return 'As senhas não coincidem'
      default:
        return `${friendlyFieldName} é inválido`
    }
  }

  // File upload helpers
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes'
    
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  validateFile(file: File, allowedTypes: string[], maxSizeInMB: number): { valid: boolean; error?: string } {
    // Check file type
    if (allowedTypes.length > 0 && !allowedTypes.some(type => 
      file.type === type || file.name.toLowerCase().endsWith(type.toLowerCase())
    )) {
      return { 
        valid: false, 
        error: `Tipo de arquivo não permitido. Tipos permitidos: ${allowedTypes.join(', ')}` 
      }
    }

    // Check file size
    const maxSizeInBytes = maxSizeInMB * 1024 * 1024
    if (file.size > maxSizeInBytes) {
      return { 
        valid: false, 
        error: `Arquivo muito grande. Tamanho máximo: ${maxSizeInMB}MB` 
      }
    }

    return { valid: true }
  }

  // Date/Time helpers
  formatDate(date: Date | string, format: string = 'dd/MM/yyyy'): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    
    if (isNaN(dateObj.getTime())) {
      return ''
    }

    const day = dateObj.getDate().toString().padStart(2, '0')
    const month = (dateObj.getMonth() + 1).toString().padStart(2, '0')
    const year = dateObj.getFullYear()

    switch (format) {
      case 'dd/MM/yyyy':
        return `${day}/${month}/${year}`
      case 'MM/dd/yyyy':
        return `${month}/${day}/${year}`
      case 'yyyy-MM-dd':
        return `${year}-${month}-${day}`
      default:
        return `${day}/${month}/${year}`
    }
  }

  formatCurrency(value: number, currency: string = 'BRL'): string {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: currency
    }).format(value)
  }

  // Loading state management
  createLoadingState(): {
    loading: boolean
    error: string | null
    setLoading: (loading: boolean) => void
    setError: (error: string | null) => void
    reset: () => void
  } {
    const state = {
      loading: false,
      error: null as string | null,
      setLoading: (loading: boolean) => { state.loading = loading },
      setError: (error: string | null) => { state.error = error },
      reset: () => {
        state.loading = false
        state.error = null
      }
    }
    return state
  }
}
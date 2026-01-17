import { Component, Input, forwardRef } from '@angular/core'
import { CommonModule } from '@angular/common'
import { ControlValueAccessor, NG_VALUE_ACCESSOR, FormsModule, ReactiveFormsModule } from '@angular/forms'
import { UiIconComponent } from '../../../shared/components/ui/icon/icon.component'

export interface ValidationRule {
  type: 'required' | 'email' | 'minLength' | 'maxLength' | 'pattern'
  value?: any
  message: string
}

/**
 * Componente de input reutilizável com validação integrada
 * Uso: <app-input label="Email" type="email" [validations]="emailValidations" />
 */
@Component({
  selector: 'app-input',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    UiIconComponent
  ],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputComponent),
      multi: true
    }
  ],
  template: `
    <div class="app-input-container mb-2 w-full" [class.error]="hasError()" [class.success]="hasSuccess()">
      <label *ngIf="label" class="block text-sm font-medium text-slate-400 mb-1 ml-1">{{ label }}</label>
      
      <div class="input-wrapper relative flex items-center bg-slate-950 border border-slate-700 rounded-lg transition-all focus-within:border-purple-500 focus-within:ring-1 focus-within:ring-purple-500"
          [class.border-red-500]="hasError()"
          [class.border-green-500]="hasSuccess()"
          [class.bg-slate-900]="disabled"
          [class.cursor-not-allowed]="disabled">
          
        <!-- Ícone prefix -->
        <div *ngIf="prefixIcon" class="pl-3 text-slate-500 flex items-center justify-center">
            <ui-icon class="text-lg">{{ prefixIcon }}</ui-icon>
        </div>
        
        <input
            class="w-full bg-transparent border-none text-white text-sm px-3 py-2.5 focus:outline-none disabled:cursor-not-allowed placeholder-slate-600"
            [type]="type"
            [placeholder]="placeholder"
            [disabled]="disabled"
            [readonly]="readonly"
            [(ngModel)]="value"
            (ngModelChange)="onChange($event)"
            (blur)="onTouched()"
            (focus)="onFocus()"
            [autocomplete]="autocomplete"
        />
        
        <div class="actions flex items-center pr-2 gap-1">
            <!-- Botão clear -->
            <button
                *ngIf="showClear && value && !disabled"
                class="p-1 text-slate-500 hover:text-white rounded-full transition-colors"
                (click)="clear()"
                type="button"
                aria-label="Clear"
            >
                <ui-icon class="text-sm">close</ui-icon>
            </button>
            
            <!-- Botão de visibilidade para senhas -->
            <button
                *ngIf="type === 'password' && showPasswordToggle"
                class="p-1 text-slate-500 hover:text-white rounded-full transition-colors"
                (click)="togglePasswordVisibility()"
                type="button"
                [attr.aria-label]="showPassword ? 'Hide password' : 'Show password'"
            >
                <ui-icon class="text-lg">{{ showPassword ? 'visibility_off' : 'visibility' }}</ui-icon>
            </button>
            
            <!-- Ícone sufix -->
            <ui-icon *ngIf="suffixIcon" class="text-slate-500 text-lg mr-1">{{ suffixIcon }}</ui-icon>
        </div>
      </div>
      
      <!-- Hint -->
      <div *ngIf="hint && !hasError()" class="mt-1 text-xs text-slate-500 ml-1">{{ hint }}</div>
      
      <!-- Erros de validação -->
      <div *ngIf="hasError()" class="mt-1 text-xs text-red-400 flex items-center gap-1 ml-1">
        <ui-icon class="text-sm">error_outline</ui-icon>
        {{ getErrorMessage() }}
      </div>
      
      <!-- Sucesso -->
      <div *ngIf="hasSuccess() && successMessage" class="mt-1 text-xs text-green-400 flex items-center gap-1 ml-1">
        <ui-icon class="text-sm">check_circle</ui-icon>
        {{ successMessage }}
      </div>
    </div>
  `,
  styles: []
})
export class InputComponent implements ControlValueAccessor {
  @Input() label = ''
  @Input() type: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' = 'text'
  @Input() placeholder = ''
  @Input() hint = ''
  @Input() prefixIcon = ''
  @Input() suffixIcon = ''
  @Input() showClear = false
  @Input() showPasswordToggle = false
  @Input() disabled = false
  @Input() readonly = false
  @Input() autocomplete = 'off'
  @Input() size: 'normal' | 'small' | 'large' = 'normal'
  @Input() variant: 'filled' | 'outline' = 'filled'
  @Input() validations: ValidationRule[] = []
  @Input() successMessage = ''
  @Input() validateOnBlur = true
  @Input() validateOnChange = false

  value = ''
  touched = false
  focused = false
  showPassword = false
  errors: string[] = []

  onChange = (value: string) => { }
  onTouched = () => { }

  writeValue(value: string): void {
    this.value = value
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled
  }

  onFocus(): void {
    this.focused = true
  }

  clear(): void {
    this.value = ''
    this.onChange('')
    this.validate()
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword
    this.type = this.showPassword ? 'text' : 'password'
  }

  validate(): void {
    this.errors = []

    for (const rule of this.validations) {
      const isValid = this.validateRule(rule)
      if (!isValid) {
        this.errors.push(rule.message)
      }
    }
  }

  private validateRule(rule: ValidationRule): boolean {
    switch (rule.type) {
      case 'required':
        return this.value.trim().length > 0
      case 'email':
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.value)
      case 'minLength':
        return this.value.length >= (rule.value || 0)
      case 'maxLength':
        return this.value.length <= (rule.value || Infinity)
      case 'pattern':
        return new RegExp(rule.value).test(this.value)
      default:
        return true
    }
  }

  hasError(): boolean {
    return this.errors.length > 0
  }

  get showSuccess(): boolean {
    return !this.hasError() && this.touched && !!this.successMessage
  }

  hasSuccess(): boolean {
    return this.showSuccess
  }

  getErrorMessage(): string {
    return this.errors[0] || ''
  }
}

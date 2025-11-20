import { Component, Input, forwardRef } from '@angular/core'
import { CommonModule } from '@angular/common'
import { ControlValueAccessor, NG_VALUE_ACCESSOR, FormsModule, ReactiveFormsModule } from '@angular/forms'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatInputModule } from '@angular/material/input'
import { MatIconModule } from '@angular/material/icon'
import { MatButtonModule } from '@angular/material/button'

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
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule
  ],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputComponent),
      multi: true
    }
  ],
  template: `
    <mat-form-field class="app-input" [class.error]="hasError()" [class.success]="hasSuccess()">
      <mat-label *ngIf="label">{{ label }}</mat-label>
      
      <input
        matInput
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
      
      <!-- Ícone prefix -->
      <mat-icon *ngIf="prefixIcon" matPrefix>{{ prefixIcon }}</mat-icon>
      
      <!-- Ícone sufix -->
      <mat-icon *ngIf="suffixIcon" matSuffix>{{ suffixIcon }}</mat-icon>
      
      <!-- Botão clear -->
      <button
        *ngIf="showClear && value && !disabled"
        mat-icon-button
        matSuffix
        (click)="clear()"
        type="button"
        aria-label="Clear"
      >
        <mat-icon>close</mat-icon>
      </button>
      
      <!-- Botão de visibilidade para senhas -->
      <button
        *ngIf="type === 'password' && showPasswordToggle"
        mat-icon-button
        matSuffix
        (click)="togglePasswordVisibility()"
        type="button"
        [attr.aria-label]="showPassword ? 'Hide password' : 'Show password'"
      >
        <mat-icon>{{ showPassword ? 'visibility_off' : 'visibility' }}</mat-icon>
      </button>
      
      <!-- Hint -->
      <mat-hint *ngIf="hint && !hasError()">{{ hint }}</mat-hint>
      
      <!-- Erros de validação -->
      <mat-error *ngIf="hasError()">
        <mat-icon>error_outline</mat-icon>
        {{ getErrorMessage() }}
      </mat-error>
      
      <!-- Sucesso -->
      <mat-hint *ngIf="hasSuccess() && successMessage" class="success-message">
        <mat-icon>check_circle</mat-icon>
        {{ successMessage }}
      </mat-hint>
    </mat-form-field>
  `,
  styles: [`
    .app-input {
      width: 100%;
      margin-bottom: 0.5rem;
    }

    .app-input.error {
      --mdc-filled-text-field-error-active-indicator-color: #f44336;
    }

    .app-input.success {
      --mdc-filled-text-field-active-indicator-color: #4caf50;
    }

    mat-error, .success-message {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.875rem;
    }

    mat-error mat-icon, .success-message mat-icon {
      font-size: 1rem;
      width: 1rem;
      height: 1rem;
    }

    /* Estados de foco */
    .app-input:focus-within {
      transform: translateY(-1px);
      transition: transform 0.2s ease;
    }

    /* Tamanhos */
    :host(.small) .app-input {
      font-size: 0.875rem;
    }

    :host(.large) .app-input {
      font-size: 1.125rem;
    }

    /* Variante outline */
    :host(.outline) .app-input {
      --mdc-outlined-text-field-container-shape: 8px;
    }
  `]
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

  onChange = (value: string) => {}
  onTouched = () => {}

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
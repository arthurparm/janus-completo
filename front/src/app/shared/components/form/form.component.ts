import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, ViewChild, TemplateRef, ContentChild } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormGroup, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms'
import { MatButtonModule } from '@angular/material/button'
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner'
import { Subject, takeUntil } from 'rxjs'

export interface FormField {
  name: string
  type: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'search' | 'select'
  label: string
  placeholder?: string
  required?: boolean
  disabled?: boolean
  validation?: {
    minLength?: number
    maxLength?: number
    pattern?: string
    patternMessage?: string
    custom?: (value: any) => { valid: boolean; message?: string }
  }
  defaultValue?: any
  options?: { value: any; label: string }[] // For select fields
}

export interface FormConfig {
  fields: FormField[]
  submitButtonText?: string
  cancelButtonText?: string
  showCancel?: boolean
  resetOnSubmit?: boolean
  validateOnSubmit?: boolean
  validateOnChange?: boolean
}

export interface FormSubmitEvent {
  valid: boolean
  value: any
  errors?: any
}

@Component({
  selector: 'app-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatProgressSpinnerModule
  ],
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()" class="app-form">
      <div class="form-fields">
        <div *ngFor="let field of config.fields" class="form-field">
          <label [for]="field.name" class="field-label">
            {{ field.label }}
            <span *ngIf="field.required" class="required-indicator">*</span>
          </label>

          <div class="field-input-container">
            <input
              *ngIf="field.type !== 'select'"
              [id]="field.name"
              [type]="field.type"
              [formControlName]="field.name"
              [placeholder]="field.placeholder || ''"
              [disabled]="field.disabled || isSubmitting"
              class="field-input"
              [class.error]="getFieldError(field.name)"
              [attr.aria-invalid]="!!getFieldError(field.name)"
              [attr.aria-describedby]="getFieldError(field.name) ? field.name + '-error' : null">

            <select
              *ngIf="field.type === 'select'"
              [id]="field.name"
              [formControlName]="field.name"
              [disabled]="field.disabled || isSubmitting"
              class="field-input field-select"
              [class.error]="getFieldError(field.name)"
              [attr.aria-invalid]="!!getFieldError(field.name)"
              [attr.aria-describedby]="getFieldError(field.name) ? field.name + '-error' : null">
              <option value="" disabled selected>{{ field.placeholder || 'Selecione...' }}</option>
              <option *ngFor="let option of field.options" [value]="option.value">
                {{ option.label }}
              </option>
            </select>

            <div *ngIf="getFieldError(field.name)" [id]="field.name + '-error'" class="field-error">
              {{ getFieldError(field.name) }}
            </div>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button
          *ngIf="config.showCancel !== false"
          type="button"
          mat-button
          (click)="onCancel()"
          [disabled]="isSubmitting"
          class="cancel-button">
          {{ config.cancelButtonText || 'Cancelar' }}
        </button>

        <button
          type="submit"
          mat-raised-button
          color="primary"
          [disabled]="form.invalid || isSubmitting"
          class="submit-button">
          <span *ngIf="!isSubmitting">{{ config.submitButtonText || 'Enviar' }}</span>
          <mat-spinner *ngIf="isSubmitting" diameter="20"></mat-spinner>
        </button>
      </div>

      <div *ngIf="submitError" class="form-error">
        {{ submitError }}
      </div>
    </form>
  `,
  styles: [`
    .app-form {
      width: 100%;
    }

    .form-fields {
      display: flex;
      flex-direction: column;
      gap: 20px;
      margin-bottom: 24px;
    }

    .form-field {
      display: flex;
      flex-direction: column;
    }

    .field-label {
      font-size: 0.875rem;
      font-weight: 500;
      color: rgba(0, 0, 0, 0.87);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
    }

    .required-indicator {
      color: #f44336;
      margin-left: 4px;
    }

    .field-input-container {
      position: relative;
    }

    .field-input {
      width: 100%;
      padding: 12px 16px;
      border: 1px solid rgba(0, 0, 0, 0.23);
      border-radius: 4px;
      font-size: 1rem;
      font-family: inherit;
      background-color: white;
      transition: border-color 0.2s, box-shadow 0.2s;
    }

    .field-input:focus {
      outline: none;
      border-color: #1976d2;
      box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2);
    }

    .field-input:hover:not(:disabled) {
      border-color: rgba(0, 0, 0, 0.87);
    }

    .field-input:disabled {
      background-color: rgba(0, 0, 0, 0.04);
      color: rgba(0, 0, 0, 0.38);
      cursor: not-allowed;
    }

    .field-input.error {
      border-color: #f44336;
    }

    .field-input.error:focus {
      border-color: #f44336;
      box-shadow: 0 0 0 2px rgba(244, 67, 54, 0.2);
    }

    .field-select {
      cursor: pointer;
    }

    .field-error {
      font-size: 0.75rem;
      color: #f44336;
      margin-top: 4px;
      display: flex;
      align-items: center;
    }

    .field-error::before {
      content: '⚠';
      margin-right: 4px;
      font-size: 0.875rem;
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      align-items: center;
    }

    .cancel-button {
      color: rgba(0, 0, 0, 0.87);
    }

    .submit-button {
      min-width: 120px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }

    .form-error {
      margin-top: 16px;
      padding: 12px 16px;
      background-color: #ffebee;
      border: 1px solid #ffcdd2;
      border-radius: 4px;
      color: #c62828;
      font-size: 0.875rem;
      display: flex;
      align-items: center;
    }

    .form-error::before {
      content: '❌';
      margin-right: 8px;
      font-size: 1rem;
    }

    @media (max-width: 768px) {
      .form-actions {
        flex-direction: column;
        gap: 8px;
      }

      .cancel-button,
      .submit-button {
        width: 100%;
      }
    }
  `]
})
export class FormComponent implements OnInit, OnDestroy {
  @Input() config!: FormConfig
  @Input() initialValues: any = {}
  @Input() isSubmitting = false
  @Input() submitError = ''
  
  @Output() submitted = new EventEmitter<FormSubmitEvent>()
  @Output() cancelled = new EventEmitter<void>()
  @Output() valueChanged = new EventEmitter<any>()

  @ContentChild('customFieldTemplate') customFieldTemplate?: TemplateRef<any>

  form!: FormGroup
  private destroy$ = new Subject<void>()

  constructor(private fb: FormBuilder) {}

  ngOnInit() {
    this.buildForm()
    this.setupFormListeners()
    this.setInitialValues()
  }

  ngOnDestroy() {
    this.destroy$.next()
    this.destroy$.complete()
  }

  private buildForm() {
    const formGroupConfig: any = {}

    this.config.fields.forEach(field => {
      const validators = []
      
      if (field.required) {
        validators.push(Validators.required)
      }
      
      if (field.validation?.minLength) {
        validators.push(Validators.minLength(field.validation.minLength))
      }
      
      if (field.validation?.maxLength) {
        validators.push(Validators.maxLength(field.validation.maxLength))
      }
      
      if (field.validation?.pattern) {
        validators.push(Validators.pattern(field.validation.pattern))
      }
      
      if (field.validation?.custom) {
        validators.push(this.createCustomValidator(field.validation.custom))
      }

      formGroupConfig[field.name] = [
        field.defaultValue || '',
        validators
      ]
    })

    this.form = this.fb.group(formGroupConfig)
  }

  private setupFormListeners() {
    if (this.config.validateOnChange) {
      this.form.valueChanges
        .pipe(takeUntil(this.destroy$))
        .subscribe(values => {
          this.valueChanged.emit(values)
        })
    }
  }

  private setInitialValues() {
    if (this.initialValues && Object.keys(this.initialValues).length > 0) {
      this.form.patchValue(this.initialValues, { emitEvent: false })
    }
  }

  private createCustomValidator(customValidator: (value: any) => { valid: boolean; message?: string }) {
    return (control: any) => {
      const result = customValidator(control.value)
      return result.valid ? null : { custom: result.message || 'Invalid value' }
    }
  }

  getFieldError(fieldName: string): string {
    const control = this.form.get(fieldName)
    if (!control || !control.errors || !control.touched) {
      return ''
    }

    const field = this.config.fields.find(f => f.name === fieldName)
    const errors = control.errors

    if (errors['required']) {
      return 'Este campo é obrigatório'
    }
    
    if (errors['email']) {
      return 'Por favor, insira um email válido'
    }
    
    if (errors['minlength']) {
      return `Mínimo ${errors['minlength'].requiredLength} caracteres`
    }
    
    if (errors['maxlength']) {
      return `Máximo ${errors['maxlength'].requiredLength} caracteres`
    }
    
    if (errors['pattern']) {
      return field?.validation?.patternMessage || 'Formato inválido'
    }
    
    if (errors['custom']) {
      return errors['custom']
    }

    return 'Campo inválido'
  }

  async onSubmit() {
    if (this.config.validateOnSubmit !== false) {
      this.form.markAllAsTouched()
    }

    const event: FormSubmitEvent = {
      valid: this.form.valid,
      value: this.form.value,
      errors: this.form.errors
    }

    this.submitted.emit(event)

    if (this.config.resetOnSubmit && this.form.valid) {
      this.form.reset()
    }
  }

  onCancel() {
    this.cancelled.emit()
  }

  reset() {
    this.form.reset()
    this.submitError = ''
  }

  getFormValue(): any {
    return this.form.value
  }

  setFormValue(values: any) {
    this.form.patchValue(values)
  }

  markAllAsTouched() {
    this.form.markAllAsTouched()
  }

  get isValid(): boolean {
    return this.form.valid
  }
}
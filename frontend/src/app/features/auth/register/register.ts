import { ChangeDetectorRef, Component, inject } from '@angular/core'
import { ReactiveFormsModule, FormBuilder, Validators, AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms'
import { RouterLink } from '@angular/router'
import { AuthService } from '../../../core/auth/auth.service'

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './register.html',
  styleUrls: ['./register.scss']
})
export class RegisterComponent {
  private fb = inject(FormBuilder)
  private auth = inject(AuthService)
  private cdr = inject(ChangeDetectorRef)
  private readonly cpfValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
    const cpf = String(control.value ?? '').replace(/\D/g, '')
    if (!cpf) return null
    if (cpf.length !== 11) return { cpfInvalid: true }
    if (/^(\d)\1{10}$/.test(cpf)) return { cpfInvalid: true }

    const calcDigit = (base: number): number => {
      let sum = 0
      for (let i = 0; i < base; i += 1) {
        sum += Number(cpf[i]) * ((base + 1) - i)
      }
      const digit = (sum * 10) % 11
      return digit === 10 ? 0 : digit
    }

    const d10 = calcDigit(9)
    const d11 = calcDigit(10)
    const valid = d10 === Number(cpf[9]) && d11 === Number(cpf[10])
    return valid ? null : { cpfInvalid: true }
  }
  private readonly passwordStrengthValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
    const value = String(control.value ?? '')
    const hasMinLength = value.length >= 8
    const hasUpper = /[A-Z]/.test(value)
    const hasLower = /[a-z]/.test(value)
    const hasNumber = /\d/.test(value)
    const hasSpecial = /[^A-Za-z0-9]/.test(value)
    return hasMinLength && hasUpper && hasLower && hasNumber && hasSpecial ? null : { passwordStrength: true }
  }
  private readonly passwordPersonalInfoValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
    const password = String(control.get('password')?.value ?? '')
    if (!password) return null
    const normalizedPassword = this.normalizeForMatch(password)
    if (!normalizedPassword) return null
    const tokens = this.collectPersonalTokens(control)
    const hit = tokens.some(token => token && normalizedPassword.includes(token))
    return hit ? { passwordContainsPersonalInfo: true } : null
  }
  form = this.fb.group({
    username: ['', [Validators.required, Validators.minLength(3), Validators.pattern(/^[a-zA-Z0-9._-]+$/)]],
    fullName: ['', [Validators.required, Validators.minLength(3)]],
    cpf: ['', [Validators.required, Validators.pattern(/^(\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2})$/), this.cpfValidator]],
    phone: ['', [Validators.required, Validators.pattern(/^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$/)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, this.passwordStrengthValidator]],
    terms: [false, Validators.requiredTrue]
  }, { validators: [this.passwordPersonalInfoValidator] })
  showPassword = false
  loading = false
  error = ''
  success = ''

  get passwordValue(): string {
    return String(this.form.controls.password.value ?? '')
  }

  get hasMinLength(): boolean {
    return this.passwordValue.length >= 8
  }

  get hasUppercase(): boolean {
    return /[A-Z]/.test(this.passwordValue)
  }

  get hasLowercase(): boolean {
    return /[a-z]/.test(this.passwordValue)
  }

  get hasNumber(): boolean {
    return /\d/.test(this.passwordValue)
  }

  get hasSpecial(): boolean {
    return /[^A-Za-z0-9]/.test(this.passwordValue)
  }

  get hasNoPersonalInfo(): boolean {
    return this.passwordValue.length > 0 && !this.form.hasError('passwordContainsPersonalInfo')
  }

  onCpfInput() {
    const control = this.form.controls.cpf
    const raw = String(control.value ?? '')
    const formatted = this.formatCpf(raw)
    if (formatted !== raw) {
      control.setValue(formatted, { emitEvent: false })
    }
  }

  onPhoneInput() {
    const control = this.form.controls.phone
    const raw = String(control.value ?? '')
    const formatted = this.formatPhone(raw)
    if (formatted !== raw) {
      control.setValue(formatted, { emitEvent: false })
    }
  }

  togglePassword() {
    this.showPassword = !this.showPassword
  }

  async register() {
    if (this.loading) return
    this.error = ''
    this.success = ''
    if (this.form.invalid) {
      this.form.markAllAsTouched()
      return
    }
    this.loading = true
    try {
      const result = await this.auth.registerLocal({
        username: String(this.form.value.username || ''),
        fullName: String(this.form.value.fullName || ''),
        cpf: String(this.form.value.cpf || ''),
        phone: String(this.form.value.phone || ''),
        email: String(this.form.value.email || ''),
        password: String(this.form.value.password || ''),
        terms: Boolean(this.form.value.terms)
      })
      if (result.ok) {
        this.success = 'Cadastro realizado. Voce ja pode acessar.'
        this.form.reset({ terms: false })
      } else {
        this.error = result.error || 'Falha ao registrar. Verifique seus dados.'
      }
    } catch {
      this.error = 'Falha ao registrar. Tente novamente.'
    } finally {
      this.loading = false
      this.cdr.markForCheck()
    }
  }

  private formatCpf(value: string): string {
    const digits = value.replace(/\D/g, '').slice(0, 11)
    if (digits.length <= 3) return digits
    if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`
    if (digits.length <= 9) {
      return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`
    }
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`
  }

  private formatPhone(value: string): string {
    const digits = value.replace(/\D/g, '').slice(0, 11)
    if (digits.length <= 2) return digits
    const ddd = digits.slice(0, 2)
    const rest = digits.slice(2)
    if (rest.length <= 4) return `(${ddd}) ${rest}`
    if (rest.length <= 8) return `(${ddd}) ${rest.slice(0, 4)}-${rest.slice(4)}`
    return `(${ddd}) ${rest.slice(0, 5)}-${rest.slice(5)}`
  }

  private normalizeForMatch(value: string): string {
    return value.toLowerCase().replace(/[^a-z0-9]/g, '')
  }

  private collectPersonalTokens(control: AbstractControl): string[] {
    const tokens = new Set<string>()
    const username = this.normalizeForMatch(String(control.get('username')?.value ?? ''))
    if (username.length >= 3) tokens.add(username)

    const email = String(control.get('email')?.value ?? '').toLowerCase()
    const emailLocal = email.split('@')[0] || ''
    const normalizedEmailLocal = this.normalizeForMatch(emailLocal)
    if (normalizedEmailLocal.length >= 3) tokens.add(normalizedEmailLocal)

    const fullName = String(control.get('fullName')?.value ?? '').toLowerCase()
    fullName.split(/\s+/).forEach(part => {
      const normalizedPart = this.normalizeForMatch(part)
      if (normalizedPart.length >= 3) tokens.add(normalizedPart)
    })

    const cpfDigits = String(control.get('cpf')?.value ?? '').replace(/\D/g, '')
    if (cpfDigits.length >= 11) tokens.add(cpfDigits)
    if (cpfDigits.length >= 4) tokens.add(cpfDigits.slice(-4))

    const phoneDigits = String(control.get('phone')?.value ?? '').replace(/\D/g, '')
    if (phoneDigits.length >= 10) tokens.add(phoneDigits)
    if (phoneDigits.length >= 4) tokens.add(phoneDigits.slice(-4))

    return Array.from(tokens)
  }
}

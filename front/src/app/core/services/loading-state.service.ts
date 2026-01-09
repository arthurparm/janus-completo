import { Injectable, signal, computed } from '@angular/core'
import { LoadingState, LoadingConfig } from '../types'

/**
 * Serviço global para gerenciamento de estados de loading
 * Fornece controle granular de loading para diferentes partes da aplicação
 */
@Injectable({
  providedIn: 'root'
})
export class LoadingStateService {
  private readonly loadingStates = signal<Map<string, LoadingState>>(new Map())
  private readonly globalLoading = signal<boolean>(false)
  private readonly httpLoading = signal<boolean>(false)

  readonly isLoading = computed(() => {
    const states = this.loadingStates()
    return states.size > 0 && Array.from(states.values()).some(state => state.isLoading)
  })

  readonly isGlobalLoading = computed(() => this.globalLoading())
  readonly isHttpLoading = computed(() => this.httpLoading())

  readonly loadingKeys = computed(() => {
    const states = this.loadingStates()
    return Array.from(states.entries())
      .filter(([, state]) => state.isLoading)
      .map(([key]) => key)
  })

  /**
   * Inicia estado de loading para uma chave específica
   */
  startLoading(key: string, config?: LoadingConfig): void
  startLoading(key: string, message?: string): void
  startLoading(key: string, configOrMessage?: LoadingConfig | string): void {
    const config: LoadingConfig = typeof configOrMessage === 'string'
      ? { message: configOrMessage }
      : configOrMessage || {}
    const currentStates = this.loadingStates()
    const newState: LoadingState = {
      isLoading: true,
      message: config?.message || '',
      progress: config?.progress || 0,
      timestamp: Date.now()
    }

    currentStates.set(key, newState)
    this.loadingStates.set(new Map(currentStates))

    if (config?.global) {
      this.globalLoading.set(true)
    }

    if (config?.http) {
      this.httpLoading.set(true)
    }
  }

  /**
   * Atualiza progresso de loading para uma chave específica
   */
  updateProgress(key: string, progress: number): void {
    const currentStates = this.loadingStates()
    const existingState = currentStates.get(key)

    if (existingState) {
      existingState.progress = progress
      this.loadingStates.set(new Map(currentStates))
    }
  }

  /**
   * Atualiza mensagem de loading para uma chave específica
   */
  updateMessage(key: string, message: string): void {
    const currentStates = this.loadingStates()
    const existingState = currentStates.get(key)

    if (existingState) {
      existingState.message = message
      this.loadingStates.set(new Map(currentStates))
    }
  }

  /**
   * Finaliza estado de loading para uma chave específica
   */
  stopLoading(key: string): void {
    const currentStates = this.loadingStates()
    const existingState = currentStates.get(key)

    if (existingState) {
      existingState.isLoading = false
      existingState.completedAt = Date.now()

      // Remove após um pequeno delay para permitir animações
      setTimeout(() => {
        const states = this.loadingStates()
        states.delete(key)
        this.loadingStates.set(new Map(states))

        // Verifica se ainda há loading global/HTTP ativo
        const hasGlobalLoading = Array.from(states.values()).some(s => s.isLoading && s.global)
        const hasHttpLoading = Array.from(states.values()).some(s => s.isLoading && s.http)

        this.globalLoading.set(hasGlobalLoading)
        this.httpLoading.set(hasHttpLoading)
      }, 300)
    }
  }

  /**
   * Verifica se uma chave específica está em loading
   */
  isKeyLoading(key: string): boolean {
    const state = this.loadingStates().get(key)
    return state?.isLoading || false
  }

  /**
   * Obtém estado de loading para uma chave específica
   */
  getLoadingState(key: string): LoadingState | undefined {
    return this.loadingStates().get(key)
  }

  /**
   * Limpa todos os estados de loading
   */
  clearAll(): void {
    this.loadingStates.set(new Map())
    this.globalLoading.set(false)
    this.httpLoading.set(false)
  }

  /**
   * Força finalização de todos os loadings ativos
   */
  forceStopAll(): void {
    const states = this.loadingStates()
    states.forEach((state, _key) => {
      state.isLoading = false
      state.completedAt = Date.now()
    })

    setTimeout(() => {
      this.clearAll()
    }, 300)
  }
}
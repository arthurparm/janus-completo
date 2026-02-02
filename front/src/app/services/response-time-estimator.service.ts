import { Injectable } from '@angular/core'

export interface ResponseTimeStats {
  avgTime: number
  minTime: number
  maxTime: number
  count: number
  lastResponseTime?: number
}

export interface ComplexityFactors {
  messageLength: number
  hasCode: boolean
  hasMultipleQuestions: boolean
  hasFileReferences: boolean
  hasComplexTerms: boolean
}

@Injectable({ providedIn: 'root' })
export class ResponseTimeEstimatorService {
  private responseHistory: number[] = []
  private maxHistorySize = 50

  // Tempos base em milissegundos
  private readonly BASE_TIMES = {
    simple: 2000,      // 2 segundos
    medium: 5000,      // 5 segundos
    complex: 10000,    // 10 segundos
    veryComplex: 20000 // 20 segundos
  }

  // Fatores de complexidade
  private readonly COMPLEXITY_FACTORS = {
    messageLength: 0.5,        // +0.5s por 100 caracteres
    hasCode: 3000,             // +3s se tiver código
    hasMultipleQuestions: 2000, // +2s se tiver múltiplas perguntas
    hasFileReferences: 4000,   // +4s se referenciar arquivos
    hasComplexTerms: 2000      // +2s se tiver termos técnicos complexos
  }

  recordResponseTime(timeMs: number): void {
    this.responseHistory.push(timeMs)

    // Limitar histórico
    if (this.responseHistory.length > this.maxHistorySize) {
      this.responseHistory.shift()
    }
  }

  getStats(): ResponseTimeStats {
    if (this.responseHistory.length === 0) {
      return {
        avgTime: this.BASE_TIMES.medium,
        minTime: this.BASE_TIMES.simple,
        maxTime: this.BASE_TIMES.complex,
        count: 0
      }
    }

    const sum = this.responseHistory.reduce((a, b) => a + b, 0)
    return {
      avgTime: sum / this.responseHistory.length,
      minTime: Math.min(...this.responseHistory),
      maxTime: Math.max(...this.responseHistory),
      count: this.responseHistory.length,
      lastResponseTime: this.responseHistory[this.responseHistory.length - 1]
    }
  }

  analyzeComplexity(message: string): ComplexityFactors {
    return {
      messageLength: message.length,
      hasCode: this.hasCodeBlocks(message),
      hasMultipleQuestions: this.hasMultipleQuestions(message),
      hasFileReferences: this.hasFileReferences(message),
      hasComplexTerms: this.hasComplexTerms(message)
    }
  }

  estimateResponseTime(message: string): number {
    const complexity = this.analyzeComplexity(message)
    const stats = this.getStats()

    // Começar com a média histórica ou tempo base
    let estimatedTime = stats.count > 0 ? stats.avgTime : this.BASE_TIMES.medium

    // Ajustar baseado na complexidade da mensagem
    if (complexity.messageLength > 200) {
      estimatedTime += (complexity.messageLength / 100) * this.COMPLEXITY_FACTORS.messageLength
    }

    if (complexity.hasCode) {
      estimatedTime += this.COMPLEXITY_FACTORS.hasCode
    }

    if (complexity.hasMultipleQuestions) {
      estimatedTime += this.COMPLEXITY_FACTORS.hasMultipleQuestions
    }

    if (complexity.hasFileReferences) {
      estimatedTime += this.COMPLEXITY_FACTORS.hasFileReferences
    }

    if (complexity.hasComplexTerms) {
      estimatedTime += this.COMPLEXITY_FACTORS.hasComplexTerms
    }

    // Limitar entre mínimo e máximo razoáveis
    const minTime = Math.max(this.BASE_TIMES.simple, stats.minTime * 0.5)
    const maxTime = Math.min(60000, Math.max(stats.maxTime * 2, this.BASE_TIMES.veryComplex)) // Máximo 60 segundos

    return Math.min(maxTime, Math.max(minTime, estimatedTime))
  }

  formatEstimatedTime(milliseconds: number): string {
    const seconds = Math.ceil(milliseconds / 1000)

    if (seconds < 5) {
      return 'alguns segundos'
    } else if (seconds < 60) {
      return `${seconds} segundos`
    } else if (seconds < 120) {
      return '1 minuto'
    } else {
      const minutes = Math.ceil(seconds / 60)
      return `${minutes} minutos`
    }
  }

  private hasCodeBlocks(message: string): boolean {
    const codeIndicators = [
      /```[\s\S]*?```/g,      // Code blocks
      /`[^`]+`/g,               // Inline code
      /function\s+\w+/g,        // Function definitions
      /const\s+\w+\s*=/g,       // Variable declarations
      /class\s+\w+/g,           // Class definitions
      /\w+\(.*\)\s*{/g          // Function calls with braces
    ]

    return codeIndicators.some(pattern => pattern.test(message))
  }

  private hasMultipleQuestions(message: string): boolean {
    const questionMarks = (message.match(/\?/g) || []).length
    return questionMarks > 1
  }

  private hasFileReferences(message: string): boolean {
    const filePatterns = [
      /\w+\.\w+/g,             // file.ext
      /\/[\w/.-]+/g,           // /path/to/file
      /\w+:\/\/[^\s]+/g         // URLs
    ]

    return filePatterns.some(pattern => pattern.test(message))
  }

  private hasComplexTerms(message: string): boolean {
    const complexTerms = [
      'arquitetura', 'implementação', 'otimização', 'performance',
      'escalabilidade', 'microserviço', 'containerização', 'devops',
      'machine learning', 'inteligência artificial', 'algoritmo',
      'complexidade', 'refatoração', 'depuração', 'análise'
    ]

    const lowerMessage = message.toLowerCase()
    return complexTerms.some(term => lowerMessage.includes(term))
  }
}

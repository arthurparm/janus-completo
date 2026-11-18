import { Injectable } from '@angular/core'
import { environment } from '../../../environments/environment'

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

const LOG_PRIORITY: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
}

@Injectable({ providedIn: 'root' })
export class AppLoggerService {
  private readonly activeLevel: LogLevel = this.resolveLevel(environment.logging?.level)

  debug(message: string, meta?: unknown): void {
    this.write('debug', message, meta)
  }

  info(message: string, meta?: unknown): void {
    this.write('info', message, meta)
  }

  warn(message: string, meta?: unknown): void {
    this.write('warn', message, meta)
  }

  error(message: string, meta?: unknown): void {
    this.write('error', message, meta)
  }

  private write(level: LogLevel, message: string, meta?: unknown): void {
    if (!this.shouldLog(level)) return

    const now = new Date().toISOString()
    const payload = meta === undefined ? undefined : this.safeSerialize(meta)
    const line = `[${now}] [${level.toUpperCase()}] ${message}`

    const sink = globalThis.console?.[level]
    if (typeof sink !== 'function') return

    if (payload === undefined) {
      sink.call(globalThis.console, line)
      return
    }

    sink.call(globalThis.console, line, payload)
  }

  private shouldLog(level: LogLevel): boolean {
    return LOG_PRIORITY[level] >= LOG_PRIORITY[this.activeLevel]
  }

  private resolveLevel(value: string | undefined): LogLevel {
    if (value === 'debug' || value === 'info' || value === 'warn' || value === 'error') {
      return value
    }
    return environment.production ? 'warn' : 'debug'
  }

  private safeSerialize(meta: unknown): unknown {
    if (meta === null || meta === undefined) return meta
    if (typeof meta !== 'object') return meta

    try {
      return JSON.parse(JSON.stringify(meta))
    } catch {
      return String(meta)
    }
  }
}

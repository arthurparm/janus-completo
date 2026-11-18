import { Component, ElementRef, HostListener, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  ServiceHealthResponse,
  SystemStatusResponse,
  SystemStatusService,
} from '../../../../core/services/system-status.service';
import { Observable } from 'rxjs';
import { gsap } from 'gsap';

type HealthSeverity = 'healthy' | 'degraded' | 'critical' | 'unknown';

interface HealthSummary {
  severity: HealthSeverity;
  label: string;
  detail: string;
  totalCount: number;
  affectedCount: number;
}

@Component({
  selector: 'app-system-hud',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './system-hud.html',
  styleUrls: ['./system-hud.scss'],
})
export class SystemHud implements OnInit {
  @ViewChild('hudRoot') hudRoot?: ElementRef<HTMLElement>;
  @ViewChild('hudPanel') hudPanel?: ElementRef<HTMLElement>;

  isOpen = false;
  systemStatus$: Observable<SystemStatusResponse>;
  servicesHealth$: Observable<ServiceHealthResponse>;
  isHealthy$: Observable<boolean>;

  constructor(private statusService: SystemStatusService) {
    this.systemStatus$ = this.statusService.getSystemStatus();
    this.servicesHealth$ = this.statusService.getServicesHealth();
    this.isHealthy$ = this.statusService.isSystemHealthy$;
  }

  ngOnInit() {
    // CSS handles the persistent indicator; GSAP is only used for panel entrance.
  }

  toggleHud(event?: Event) {
    event?.stopPropagation();
    this.isOpen = !this.isOpen;

    if (this.isOpen) {
      this.animateOpen();
    } else {
      this.animateClose();
    }
  }

  getHealthSummary(response: ServiceHealthResponse | null | undefined): HealthSummary {
    const services = response?.services ?? [];
    if (services.length === 0) {
      return {
        severity: 'unknown',
        label: 'Sem telemetria',
        detail: 'Nenhum servico reportou status agora.',
        totalCount: 0,
        affectedCount: 0,
      };
    }

    const affected = services.filter(service => service.status !== 'ok');
    const errorCount = services.filter(service => service.status === 'error').length;
    const degradedCount = services.filter(service => service.status === 'degraded').length;
    const unknownCount = services.filter(service => service.status === 'unknown').length;

    if (errorCount > 0) {
      return {
        severity: 'critical',
        label: 'Critico',
        detail: `${errorCount} servico(s) em erro. Acao operacional necessaria.`,
        totalCount: services.length,
        affectedCount: affected.length,
      };
    }
    if (degradedCount > 0) {
      return {
        severity: 'degraded',
        label: 'Degradado',
        detail: `${degradedCount} servico(s) degradado(s). Experiencia pode piorar.`,
        totalCount: services.length,
        affectedCount: affected.length,
      };
    }
    if (unknownCount > 0) {
      return {
        severity: 'unknown',
        label: 'Telemetria parcial',
        detail: `${unknownCount} servico(s) sem telemetria confiavel.`,
        totalCount: services.length,
        affectedCount: affected.length,
      };
    }
    return {
      severity: 'healthy',
      label: 'Estavel',
      detail: `${services.length} servico(s) operando normalmente.`,
      totalCount: services.length,
      affectedCount: 0,
    };
  }

  getIconForService(key: string): string {
    switch (key) {
      case 'agent':
        return 'AG';
      case 'knowledge':
        return 'KG';
      case 'memory':
        return 'MEM';
      case 'llm':
        return 'LLM';
      case 'workers':
        return 'WRK';
      default:
        return 'SYS';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'ok':
        return 'OK';
      case 'degraded':
        return 'Degradado';
      case 'error':
        return 'Critico';
      case 'unknown':
        return 'Sem telemetria';
      default:
        return 'Indefinido';
    }
  }

  getStatusDescription(status: string): string {
    switch (status) {
      case 'ok':
        return 'Operando normalmente';
      case 'degraded':
        return 'Disponivel, mas com degradacao';
      case 'error':
        return 'Falha que exige acao';
      case 'unknown':
        return 'Sinal insuficiente para afirmar saude';
      default:
        return 'Estado nao reconhecido';
    }
  }

  getCapabilityLabel(service: { capability?: string; name: string }): string {
    return service.capability || service.name;
  }

  getUserImpact(service: { user_impact?: string; status: string }): string {
    if (service.user_impact) {
      return service.user_impact;
    }
    return this.getStatusDescription(service.status);
  }

  getRecommendedAction(service: { recommended_action?: string }): string | null {
    return service.recommended_action || null;
  }

  formatUptime(seconds: number | null | undefined): string {
    if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0) {
      return 'uptime indisponivel';
    }
    return `${Math.round(seconds)}s uptime`;
  }

  getStatusClass(status: string): string {
    switch (status) {
      case 'ok':
        return 'status-ok';
      case 'degraded':
        return 'status-degraded';
      case 'error':
        return 'status-error';
      case 'unknown':
      default:
        return 'status-unknown';
    }
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    if (!this.isOpen) return;
    const root = this.hudRoot?.nativeElement;
    const target = event.target as Node | null;
    if (root && target && !root.contains(target)) {
      this.isOpen = false;
    }
  }

  private animateOpen() {
    setTimeout(() => {
      const panel = this.hudPanel?.nativeElement;
      if (!panel) return;

      gsap.fromTo(
        panel,
        { opacity: 0, y: -12, scale: 0.98 },
        { opacity: 1, y: 0, scale: 1, duration: 0.24, ease: 'power2.out' }
      );

      const items = panel.querySelectorAll('.hud-item');
      if (items.length > 0) {
        gsap.fromTo(
          items,
          { opacity: 0, y: 8 },
          { opacity: 1, y: 0, duration: 0.18, stagger: 0.04, delay: 0.04 }
        );
      }
    }, 0);
  }

  private animateClose() {
    // The template removes the panel immediately; keep this hook for future exit animation.
  }
}

import { Component, OnInit, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SystemStatusService, ServiceHealthResponse, SystemStatusResponse } from '../../../../core/services/system-status.service';
import { Observable } from 'rxjs';
import { gsap } from 'gsap';

@Component({
  selector: 'app-system-hud',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './system-hud.html',
  styleUrls: ['./system-hud.scss'],
})
export class SystemHud implements OnInit {
  @ViewChild('hudPanel') hudPanel!: ElementRef;
  @ViewChild('pulseIndicator') pulseIndicator!: ElementRef;

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
    // Inicia animação de pulso contínuo
    // Nota: A animação real será feita via CSS para performance, 
    // mas usaremos GSAP para a abertura do painel.
  }

  toggleHud() {
    this.isOpen = !this.isOpen;
    
    if (this.isOpen) {
      this.animateOpen();
    } else {
      this.animateClose();
    }
  }

  private animateOpen() {
    // GSAP animation para entrada futurista
    setTimeout(() => {
      if (this.hudPanel) {
        gsap.fromTo(this.hudPanel.nativeElement, 
          { opacity: 0, y: -20, scale: 0.95 },
          { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: 'back.out(1.7)' }
        );
        
        // Animar itens individualmente (stagger)
        const items = this.hudPanel.nativeElement.querySelectorAll('.hud-item');
        gsap.fromTo(items,
          { opacity: 0, x: -20 },
          { opacity: 1, x: 0, duration: 0.3, stagger: 0.1, delay: 0.1 }
        );
      }
    }, 0); // Tick para garantir renderização do *ngIf
  }

  private animateClose() {
    // A lógica de fechar é tratada pelo *ngIf, mas se quiséssemos animar a saída:
    // gsap.to(...) e depois setar isOpen = false no onComplete
  }

  getIconForService(key: string): string {
    switch (key) {
      case 'agent': return '🤖';
      case 'knowledge': return '📚';
      case 'memory': return '🧠';
      case 'llm': return '⚡';
      default: return '🔧';
    }
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'ok': return 'bg-green-500';
      case 'degraded': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  }
}

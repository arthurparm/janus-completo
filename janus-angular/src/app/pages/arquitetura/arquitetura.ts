import {Component, OnInit, OnDestroy} from '@angular/core';

@Component({
  selector: 'app-arquitetura',
  imports: [],
  templateUrl: './arquitetura.html',
  styleUrl: './arquitetura.scss'
})
export class Arquitetura implements OnInit, OnDestroy {
  private rotatingInterval: any;
  private currentRotatingIndex = 0;

  // Conteúdo rotativo para testar capacidades de re-análise
  rotatingContent = [
    {
      title: "Estado Inicial",
      content: "Sistema em modo de espera. Aguardando entrada do usuário.",
      metrics: {cpu: "12%", memory: "2.1GB", latency: "45ms"}
    },
    {
      title: "Processamento Ativo",
      content: "IA analisando requisição. Múltiplos modelos em execução simultânea.",
      metrics: {cpu: "87%", memory: "4.8GB", latency: "120ms"}
    },
    {
      title: "Síntese de Resposta",
      content: "Consolidando resultados dos diferentes módulos cognitivos.",
      metrics: {cpu: "65%", memory: "3.2GB", latency: "78ms"}
    },
    {
      title: "Entrega Finalizada",
      content: "Resposta gerada e otimizada. Sistema retornando ao estado base.",
      metrics: {cpu: "23%", memory: "2.4GB", latency: "52ms"}
    }
  ];

  ngOnInit() {
    // Inicia rotação de conteúdo após 5 segundos
    setTimeout(() => {
      this.startContentRotation();
    }, 5000);
  }

  ngOnDestroy() {
    if (this.rotatingInterval) {
      clearInterval(this.rotatingInterval);
    }
  }

  startContentRotation() {
    this.rotatingInterval = setInterval(() => {
      this.currentRotatingIndex = (this.currentRotatingIndex + 1) % this.rotatingContent.length;
      this.updateRotatingContent();
    }, 4000);
  }

  updateRotatingContent() {
    const element = document.getElementById('rotatingInfo');
    if (element) {
      const current = this.rotatingContent[this.currentRotatingIndex];
      element.innerHTML = `
        <div>
          <h4 style="color: var(--orange); margin-bottom: 8px;">${current.title}</h4>
          <p style="margin-bottom: 12px;">${current.content}</p>
          <div class="metrics">
            <span class="metric">CPU: ${current.metrics.cpu}</span>
            <span class="metric">RAM: ${current.metrics.memory}</span>
            <span class="metric">Latência: ${current.metrics.latency}</span>
          </div>
        </div>
      `;
    }
  }

  revealHiddenContent() {
    const hiddenContent = document.getElementById('hiddenContent');
    const button = document.getElementById('revealBtn');

    if (hiddenContent && button) {
      hiddenContent.classList.add('revealed');
      button.textContent = 'Conteúdo Revelado ✓';
      (button as HTMLButtonElement).disabled = true;

      // Simula carregamento de dados críticos
      setTimeout(() => {
        const criticalData = document.getElementById('criticalData');
        if (criticalData) {
          criticalData.innerHTML = `
            <strong>DADOS CRÍTICOS CARREGADOS:</strong><br>
            • Chave de API: janus_${Math.random().toString(36).substr(2, 9)}<br>
            • Token de Sessão: ${Date.now().toString(16)}<br>
            • Endpoint Ativo: https://api.janus.ai/v2/cognitive-core<br>
            • Status: OPERACIONAL ✓
          `;
        }
      }, 1000);
    }
  }

  getCurrentRotatingContent() {
    return this.rotatingContent[this.currentRotatingIndex];
  }
}

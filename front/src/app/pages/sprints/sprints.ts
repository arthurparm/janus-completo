import { Component, OnInit, OnDestroy } from '@angular/core';

@Component({
  selector: 'app-sprints',
  imports: [],
  templateUrl: './sprints.html',
  styleUrl: './sprints.scss'
})
export class Sprints implements OnInit, OnDestroy {
  private observer?: IntersectionObserver;
  private scrollHandler?: () => void;
  private readonly initialStaticCount = 4; // itens estáticos no HTML
  private isLoading = false;
  allLoaded = false;
  displayedSprints: { id: number; title: string; focus: string; summary: string }[] = [];
  private allSprints = [
    {
      id: 1,
      title: 'Sprint 1: Espinha Dorsal do Sistema – Fundamentos de Comunicação Distribuída',
      focus: 'Infraestrutura',
      summary:
        'Foco Principal: Estabelecer uma arquitetura de comunicação assíncrona e distribuída. Implementações Chave: Integração e configuração do RabbitMQ como o principal message broker; padrão Orquestrador-Worker; canais de eventos.'
    },
    {
      id: 2,
      title: 'Sprint 2: Núcleo Cognitivo – Aprendizagem Baseada em Experiências',
      focus: 'Memória',
      summary:
        'Foco Principal: Desenvolver a capacidade de aprendizagem do Janus através de uma Memória Episódica. Implementações Chave: Qdrant como banco de dados vetorial; indexação de experiências; recuperação contextual.'
    },
    {
      id: 3,
      title: 'Sprint 3: Base de Conhecimento – Memória Semântica e Ontologias',
      focus: 'Conhecimento',
      summary:
        'Foco Principal: Construir memória semântica e grafos de conhecimento. Implementações Chave: embeddings; relacionamento conceitual; ingestão de documentação técnica.'
    },
    {
      id: 4,
      title: 'Sprint 4: Planejamento Cognitivo – Orquestração de Modelos e Ferramentas',
      focus: 'Cognitivo',
      summary:
        'Foco Principal: Orquestrar fluxo de pensamento entre diferentes modelos e ferramentas. Implementações Chave: orchestrator; uso de ferramentas; encadeamentos de raciocínio.'
    },
    {
      id: 5,
      title: 'Sprint 5: Reflexão e Melhoria – Auto-crítica e Aprimoramento',
      focus: 'Reflexão',
      summary:
        'Foco Principal: Implementar mecanismos de reflexão. Implementações Chave: avaliações pós-ação; consolidação de memória; ajuste de planos.'
    },
    {
      id: 6,
      title: 'Sprint 6: Autonomia Operacional – Gatilhos e Agendamento Proativo',
      focus: 'Autonomia',
      summary:
        'Foco Principal: Tornar o sistema proativo. Implementações Chave: agendamento de tarefas; gatilhos baseados em métricas; execução sem supervisão.'
    },
    {
      id: 7,
      title: 'Sprint 7: Observabilidade – Telemetria, Logs e Performance',
      focus: 'Observabilidade',
      summary:
        'Foco Principal: Medir e observar o comportamento. Implementações Chave: Prometheus + Grafana; métricas de LLM; tracing de fluxos.'
    },
    {
      id: 8,
      title: 'Sprint 8: Otimização – Eficiência de Modelos e Fluxos',
      focus: 'Otimização',
      summary:
        'Foco Principal: Otimizar custos e latência. Implementações Chave: cache inteligente; seleção adaptativa de modelos; paralelização controlada.'
    },
    {
      id: 9,
      title: 'Sprint 9: Colaboração – Múltiplos Agentes e Coordenação',
      focus: 'Colaboração',
      summary:
        'Foco Principal: Coordenação multiagente. Implementações Chave: papéis; mensagens entre agentes; consenso e arbitragem.'
    },
    {
      id: 10,
      title: 'Sprint 10: Ferramentas e Integrações – API e Execução Segura',
      focus: 'Ferramentas',
      summary:
        'Foco Principal: Expandir capacidades com ferramentas. Implementações Chave: catálogo de ferramentas; execução sandbox; integrações externas.'
    },
    {
      id: 11,
      title: 'Sprint 11: Sandbox e Análise de Código – Raciocínio sobre Bases',
      focus: 'Sandbox',
      summary:
        'Foco Principal: Analisar bases de código com segurança. Implementações Chave: execução isolada; indexação de repositórios; explicações técnicas.'
    },
    {
      id: 12,
      title: 'Sprint 12: Orquestração Avançada – LangGraph e Fluxos Complexos',
      focus: 'Orquestração',
      summary:
        'Foco Principal: Fluxos avançados de decisão. Implementações Chave: LangGraph; edges condicionais; controle de estado conversacional.'
    },
    {
      id: 13,
      title: 'Sprint 13: O Meta-Agente – Consciência Proativa e Auto-Orquestração',
      focus: 'Meta-Agente',
      summary:
        'Foco Principal: Meta-Agente que supervisiona e dispara ações. Implementações Chave: objetivos de alto nível; supervisão contínua; auto-orquestração.'
    }
  ];

  ngOnInit(): void {
    // Observa itens para efeito de surgimento
    this.setupObserver();
    this.observeExistingItems();
    // Atualiza linha de progresso da timeline conforme scroll
    this.scrollHandler = () => this.updateTimelineFill();
    window.addEventListener('scroll', this.scrollHandler, { passive: true });
    this.updateTimelineFill();

    // Carregar todos os sprints de uma vez (removendo paginação)
    this.displayedSprints = this.allSprints.slice(this.initialStaticCount);
    this.allLoaded = true;

    // Observar novos itens inseridos
    setTimeout(() => this.observeExistingItems(), 0);
  }

  ngOnDestroy(): void {
    if (this.observer) this.observer.disconnect();
    if (this.scrollHandler) window.removeEventListener('scroll', this.scrollHandler);
  }

  loadMore(): void {
    const btn = document.getElementById('loadMoreBtn') as HTMLButtonElement | null;
    if (!btn || this.isLoading) return;

    const renderedBefore = this.getLoadedCount();
    if (renderedBefore >= this.allSprints.length) return;

    this.isLoading = true;
    btn.classList.add('loading');
    btn.setAttribute('aria-busy', 'true');

    setTimeout(() => {
      const remainingBefore = this.allSprints.length - renderedBefore;
      const nextCount = Math.min(4, remainingBefore);
      const start = renderedBefore;
      const slice = this.allSprints.slice(start, start + nextCount);
      this.displayedSprints.push(...slice);

      btn.classList.remove('loading');
      btn.setAttribute('aria-busy', 'false');

      const renderedAfter = this.getLoadedCount();
      const label = btn.querySelector('.label');
      if (renderedAfter >= this.allSprints.length) {
        if (label) label.textContent = 'Todos os Sprints carregados ✓';
        btn.disabled = true;
      } else {
        if (label) label.textContent = 'Carregar Mais Sprints';
        btn.disabled = false;
      }

      this.isLoading = false;
      // Observe novos itens renderizados pelo Angular
      setTimeout(() => this.observeExistingItems(), 0);
    }, 1200);
  }

  private setupObserver() {
    this.observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            this.observer?.unobserve(entry.target);
          }
        }
      },
      { root: null, threshold: 0.15 }
    );
  }

  private observeExistingItems() {
    document.querySelectorAll('.timeline-item').forEach((item) => {
      if (!item.classList.contains('visible')) {
        this.observer?.observe(item);
      }
    });
  }

  private updateTimelineFill() {
    const timeline = document.getElementById('timeline');
    const line = document.getElementById('timelineLine');
    if (!timeline || !line) return;

    const rect = timeline.getBoundingClientRect();
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    const visibleBottom = Math.min(rect.height, Math.max(0, viewportHeight - rect.top));
    const percent = Math.max(0, Math.min(100, (visibleBottom / rect.height) * 100));
    line.style.setProperty('--line-fill', `${percent}%`);
  }

  private getLoadedCount(): number {
    return this.initialStaticCount + this.displayedSprints.length;
  }

  private buildTimelineItem(s: { id: number; title: string; focus: string; summary: string }): HTMLElement {
    const el = document.createElement('article');
    el.className = 'timeline-item';
    el.setAttribute('data-sprint', String(s.id));
    el.innerHTML = `
      <div class="timeline-card">
        <div class="tag">Foco: ${s.focus}</div>
        <h3>${s.title}</h3>
        <p>${s.summary}</p>
      </div>
    `;
    return el;
  }

  trackById(index: number, item: { id: number }) {
    return item.id;
  }
}

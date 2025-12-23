## Visão Geral
- Criar uma Landing Page de alto desempenho em Angular (repo está em Angular 20) com GSAP.
- Estruturar componentes: `Hero`, `About`, `WhiteCanvasEffect` e `StackGrid`.
- Implementar `ThemeService` com Angular Signals para alternar contextos (`white-canvas` → `rpg` → `ai`) via `HostBinding` e variáveis CSS globais com `transition: 0.8s`.

## Compatibilidade e Dependências
- O projeto já usa Angular 20 (`package.json`). Angular Signals estão disponíveis e equivalentes ao Angular 19.
- Adicionar dependências: `gsap` (e plugin `ScrollTrigger`).
- Tipografia: importar `Inter` (corpo) e uma Sans-Serif geométrica para títulos (ex.: `Montserrat`).

## Arquitetura de Pastas
- `src/app/core/services/theme.service.ts` — serviço de temas com Signals.
- `src/styles.scss` — variáveis CSS e temas por `data-context`.
- `src/app/pages/white-canvas/` — página principal com composição dos componentes.
- `src/app/shared/components/stack-grid/stack-grid.component.ts` — grade da stack.
- `src/app/shared/components/white-canvas-effect/white-canvas-effect.component.ts` — efeito interativo em Canvas.
- `src/app/pages/white-canvas/hero/` — componente Hero.
- `src/app/pages/white-canvas/about/` — seção About com GSAP ScrollTrigger.

## Variáveis Globais e Tipografia
- Em `index.html`, adicionar links das fontes `Inter` e `Montserrat` (ou ajustar para fonte geométrica preferida).
- Em `styles.scss`:
```scss
:root {
  --font-body: 'Inter', system-ui, sans-serif;
  --font-title: 'Montserrat', system-ui, sans-serif;
  --bg: #FFFFFF;
  --fg: #111111;
  --accent: #000000;
  --transition: 0.8s ease;
}
:root { transition: color var(--transition), background-color var(--transition), filter var(--transition); }
:root[data-context="white-canvas"] { --bg: #FFFFFF; --fg: #111; --accent: #000; }
:root[data-context="rpg"] { --bg: #0e0a0a; --fg: #e8d5b7; --accent: #9b6b3d; --font-title: 'Cinzel', serif; }
:root[data-context="ai"] { --bg: #0b1020; --fg: #cfe3ff; --accent: #5ad1ff; --font-title: 'IBM Plex Sans', sans-serif; }
html, body { background: var(--bg); color: var(--fg); font-family: var(--font-body); }
.h1, h1, .title { font-family: var(--font-title); }
```

## ThemeService (Signals)
- `src/app/core/services/theme.service.ts`:
```ts
import { Injectable, signal, computed } from '@angular/core';
export type Context = 'white-canvas' | 'rpg' | 'ai';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly context = signal<Context>('white-canvas');
  readonly themeName = computed(() => this.context());
  setContext(ctx: Context) { this.context.set(ctx); }
}
```

## HostBinding no Componente Raiz
- Em `src/app/app.ts` (ou `main-layout.ts` se preferir manter layout):
```ts
import { Component, HostBinding, inject } from '@angular/core';
import { ThemeService } from './core/services/theme.service';

@Component({ selector: 'app-root', templateUrl: './app.html', styleUrls: ['./app.scss'] })
export class AppComponent {
  private theme = inject(ThemeService);
  @HostBinding('attr.data-context') get dataContext() { return this.theme.themeName(); }
}
```
- Isso aplica `data-context` no host para que as variáveis CSS mudem suavemente.

## Componente WhiteCanvasEffect (Canvas)
- `white-canvas-effect.component.ts`: Canvas fullscreen com partículas/distorção reagindo ao mouse.
- API:
  - `@Input() intensity = 0.4` (força do efeito).
  - Usa `requestAnimationFrame`, `PointerEvent` e `ResizeObserver` para alta performance.
- Estrutura:
```ts
@Component({ selector: 'white-canvas-effect', template: '<canvas #cnv></canvas>', styles: [':host{position:fixed;inset:0;pointer-events:none} canvas{width:100%;height:100%}'] })
export class WhiteCanvasEffectComponent implements AfterViewInit, OnDestroy {
  @ViewChild('cnv', { static: true }) canvas!: ElementRef<HTMLCanvasElement>;
  private ctx!: CanvasRenderingContext2D;
  private rafId = 0; private mouse = { x: 0, y: 0 };
  ngAfterViewInit() { /* init ctx, grid, loop, listeners */ }
  ngOnDestroy() { cancelAnimationFrame(this.rafId); }
}
```

## Componente Hero
- Conteúdo exigido:
  - Nome: `Arthur Paraiso Martins`.
  - Headline: `Engenheiro de Software Full-Stack Sênior & Sócio na Queli Arte`.
- Layout minimalista centralizado, alto contraste, espaço negativo.
- Botões para alternar `Context` (`white-canvas`, `rpg`, `ai`) usando `ThemeService`.

## Seção About com GSAP ScrollTrigger
- Texto destacado: `Aos 24 anos, não construo apenas sistemas; projeto experiências de alto desempenho`.
- Registrar plugin:
```ts
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
ngAfterViewInit() { gsap.registerPlugin(ScrollTrigger); /* animações */ }
```
- Efeito: revelar e enfatizar palavras-chave ao entrar na viewport com leve blur/opacity e `clip-path`.

## StackGrid (Ficha Técnica)
- Grade responsiva mostrando: Java (6 anos), Angular (6 anos), SQL (6 anos), Docker (6 anos), C# (2 anos), Python (1 ano).
- Acessível (semântica e foco), animado com `gsap.fromTo` em `IntersectionObserver` ou `ScrollTrigger`.

## Rotas e Página
- Adicionar rota `/white-canvas` em `app.routes.ts` apontando para página `WhiteCanvasPage` (standalone) que compõe `WhiteCanvasEffect`, `Hero`, `About`, `StackGrid`.
- Mantém a arquitetura atual de páginas (`src/app/pages/...`) e padrões de nome do repo.

## Acessibilidade e Performance
- Usar `prefers-reduced-motion` para reduzir animações.
- `pointer-events: none` no Canvas para não obstruir interação.
- Evitar overdraw; limitar partículas conforme `deviceMemory` e `window.innerWidth`.

## Testes
- Unit: `ThemeService` (mudar contexto altera `data-context`), smoke test dos componentes.
- Visual: verificação manual da transição suave e reatividade do Canvas.

## Entregáveis
- Código dos componentes e serviço (standalone) seguindo padrões do repo.
- Variáveis CSS globais com transições e tipografia carregada.
- Página `/white-canvas` funcional com GSAP e Canvas.

## Próximos Passos
- Instalar `gsap` e criar os componentes/serviço conforme estrutura.
- Integrar rota e validar em dev server.

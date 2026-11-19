# Fontes

Leitura usada para o desenho. Secundárias entram onde o documento primário não listou os itens no acesso.

| Fonte | Uso no Janus |
|---|---|
| [AI Agent Architecture](https://aisuperior.com/blog/ai-agent-architecture/), AI Superior, 5 nov 2026 | Oito componentes. O modelo propõe e o código decide. Memória longa começa desligada. Traço alimenta a avaliação |
| [Governed, observable loop](https://aws.amazon.com/blogs/architecture/inside-an-enterprise-ai-agent-a-governed-observable-loop-architecture/), AWS Architecture Blog, 12 nov 2026 | Loop em fases, autonomia graduada, ferramenta com schema e efeito declarado |
| [AI agent architecture](https://www.netguru.com/blog/ai-agent-architecture), Netguru, 5 nov 2026 | Um agente mais ferramentas. Agente extra só para separar permissão. Guardrail fora do modelo |
| [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), publicado em 9 dez 2025 | ASI01–ASI10 como modelo de ameaça |
| [OWASP Agentic Top 10, item a item](https://www.querynow.com/ai-agents/security/owasp-agentic-top-10), revisão de 15 nov 2026 | Nome e controle de cada ASI, conferidos porque a página da OWASP consultada não devolveu a lista |
| [The Agent-Team Model](https://axiomstudio.ai/blog/the-agent-team-model-pm-architect-developer-qa-security-as-specialised-roles), Axiom Studio, 3 mai 2026 | Handoff tipado entre arquitetura, desenvolvimento, QA e segurança |
| [Roadmap to agentic AI systems](https://www.kdnuggets.com/the-roadmap-to-mastering-agentic-ai-systems-in-2026), KDnuggets, 17 nov 2026 | Avaliação da trajetória, não só da resposta final |
| Anthropic, *Demystifying evals for AI agents*, jan 2026 | Citado pela AI Superior: o transcript de avaliação é o traço de produção |
| Padrão MemRL, catálogo Agentic Patterns, 13 out 2026 | A voz permanece congelada. A utilidade aprendida muda com o resultado, não com o texto do modelo |
| Nasr, Carlini et al., *The Attacker Moves Second*, out 2025 | Citado pela AI Superior: ataque adaptativo fura defesa que mora no prompt |
| AI Act, artigo 50 | A AI Superior reporta dever de transparência em vigor desde 2 ago 2026. A entrada avisa que a voz é um modelo. Isto não é parecer jurídico |

## Método

Fontes abertas para [metodos.md](metodos.md). O algoritmo da fonte não entra no runtime por estar nesta tabela.

| Fonte | Uso no Janus |
|---|---|
| [Karl Popper, Stanford Encyclopedia of Philosophy](https://plato.stanford.edu/entries/popper/), revisão de 31 jul 2026 | Falseabilidade como demarcação. Critério de refutação antes do teste. Corroboração não verifica |
| [Nosek, Ebersole, DeHaven e Mellor, *The preregistration revolution*](https://doi.org/10.1073/pnas.1708274114), PNAS, 2018 | Plano antes do desfecho. Predição distinta de postdição. O pré-registro não tem, no artigo, prova experimental suficiente de que aumenta a reprodutibilidade |
| [Lopez-Paz e Ranzato, *Gradient Episodic Memory*](https://arxiv.org/abs/1706.08840), arXiv:1706.08840 | BWT, FWT e esquecimento como BWT negativo grande. Avaliação na partição de teste. Não adotamos o algoritmo |
| [Manheim e Garrabrant, *Categorizing Variants of Goodhart's Law*](https://arxiv.org/abs/1803.04585), arXiv:1803.04585 | Quatro mecanismos: regressivo, extremal, causal, adversarial |
| [Krakovna et al., *Specification gaming*](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/), Google DeepMind, 21 abr 2020 | Especificação literal satisfeita sem o resultado pretendido. Tampering da representação do objetivo |
| [Schulman et al., *Trust Region Policy Optimization*](https://arxiv.org/abs/1502.05477), arXiv:1502.05477 | Passo limitado por região de confiança. O teto linear não herda a garantia |
| [Amodei et al., *Concrete Problems in AI Safety*](https://arxiv.org/abs/1606.06565), arXiv:1606.06565 | Exploração não pode ter consequência irrecuperável. Leitura do resumo e da visão geral |
| [Grinsztajn et al., *There Is No Turning Back*](https://arxiv.org/abs/2106.04480), arXiv:2106.04480 | Ação irreversível não é exploração livre. O classificador de reversibilidade não é o portão |
| [Lakkaraju et al., *The Selective Labels Problem*](https://doi.org/10.1145/3097983.3098066), KDD 2017 | Desfecho só existe para a ação tomada. Não imputar. Contraction não entra |
| [Sheikholeslami et al., *AutoAblation*](https://doi.org/10.1145/3437984.3458834), EuroMLSys 2021 | Um componente de fora por ensaio |
| [Hardt, *Holdout method*](https://mlbenchmarks.org/pdf/04-holdout-method.pdf), capítulo 4, pré-publicação, 2026 | Não avaliar o preditor no conjunto que o treinou |
| [CTTI, Data Monitoring Committees](https://ctti-clinicaltrials.org/about/ctti-projects/data-monitoring-committees/ctti-recommendations-data-monitoring-committees/), 26 mar 2025 | Continuar, mudar ou encerrar por benefício e risco. Não redesenhar o ensaio depois do dado |

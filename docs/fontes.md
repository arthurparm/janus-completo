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
| [Anthropic, *Demystifying evals for AI agents*](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), 9 jan 2026 | Transcript, outcome e grader. O aceite do Janus usa grader de código. Juiz por modelo não é critério único |
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

## Especialização da equipe

Fontes abertas para [especialistas.md](especialistas.md). Nenhuma delas autoriza agente extra no runtime, juiz por modelo como aceite, nem defesa que mora no prompt.

| Fonte | Uso no Janus |
|---|---|
| [Schluntz e Zhang, *Building effective agents*](https://www.anthropic.com/engineering/building-effective-agents), Anthropic, 19 dez 2024 | Workflow tem caminho pré-definido. Agente é modelo em loop. A equipe é workflow. O runtime é o loop. ACI: a ferramenta é desenhada para o modelo, com borda e exemplo |
| [Cemri et al., *Why Do Multi-Agent LLM Systems Fail?*](https://arxiv.org/abs/2503.13657), arXiv:2503.13657, v3 de 26 out 2025 | MAST: 14 modos em desenho, desalinhamento e verificação. Serve para nomear falha da equipe e do harness. O anotador por modelo do artigo não é o aceite |
| [Jimenez et al., *SWE-bench*](https://arxiv.org/abs/2310.06770), ICLR 2024 | Resolução exige teste que falhava e passa, e teste que já passava e continua. Não adotamos a nota do benchmark |
| [Epoch AI, revisão do SWE-bench Verified](https://epoch.ai/benchmarks/swe-bench-verified/review), 3 set 2026 | A suíte pode rejeitar correção válida. Verde não verifica o objetivo |
| [OpenAI, *Separating signal from noise in coding evaluations*](https://openai.com/index/separating-signal-from-noise-coding-evaluations/), 8 jul 2026 | Teste estrito demais e enunciado incompleto quebram a nota. Os outros dois rótulos da auditoria não foram abertos aqui |
| [Greshake et al., *Indirect prompt injection*](https://arxiv.org/abs/2302.12173), AISec 2023 | Conteúdo recuperado entra como instrução. Controle é o portão, não o modelo distinguir sozinho |
| [Wallace et al., *The Instruction Hierarchy*](https://arxiv.org/abs/2404.13208), arXiv:2404.13208, 2024 | Hierarquia treinada no modelo não é o nosso controle. O artigo reporta ganho de robustez em GPT-3.5. Não adotamos o treino |

## Qualidade de organização

Fontes abertas para a regra 8 de [regras.md](regras.md). Nenhuma delas manda reescrever teste já aceito, trocar o runner, nem tratar suíte verde como aprendizado.

| Fonte | Uso no Janus |
|---|---|
| [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), seção 3.16 | `lower_with_under` para módulo e função, `CapWords` para classe, `CAPS_WITH_UNDER` para constante, `_` para nome interno. Teste novo: `test_<método>_<estado>`. Arquivo `.py` sem hífen. Não adotamos o teto de 80 colunas, o `pylint` como portão, nem o teto de função: a seção 3.18 só pede para pensar em quebrar perto de 40 linhas |
| [PEP 8](https://peps.python.org/pep-0008/#descriptive-naming-styles) | O guia do Google aponta esta página para o estilo de nome. Não adotamos o limite de 79 colunas |
| [unittest](https://docs.python.org/3/library/unittest.html), biblioteca padrão | Método descoberto começa com `test`. Arquivo importável a partir do topo do projeto. Se o diretório inicial não é o topo, `--top-level-directory` (`-t`) é obrigatório. Daí `discover -s tests -t .` |
| [pytest, Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html) | Testes fora do pacote e pacote em `src/`, para o teste não esconder o runtime. Não trocamos o runner |
| [Kent Beck, *Test Desiderata*](https://medium.com/@kentbeck_7670/test-desiderata-94150638a4b3), 19 out 2019 | Isolado, específico, determinístico e sensível ao comportamento. Não adotamos "inspirar" nem "apto para produção" como aceite |
| [Gerard Meszaros, *xUnit Test Patterns*, organização](http://xunitpatterns.com/Organization.html) | Uma condição por método. Quatro fases: preparar, exercer, verificar, desmontar. O nome junta a condição e o resultado esperado. Não adotamos uma classe por fixture, nem um único assert |
| [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html), definição pública de manutenibilidade | Modularidade: mudança num componente mexe pouco nos outros. Testabilidade: dá para estabelecer o critério e rodar o teste. As outras características do modelo não viram checklist |

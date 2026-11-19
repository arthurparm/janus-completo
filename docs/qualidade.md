# Qualidade

A avaliação olha a trajetória, não a frase final. O traço é o transcript do run. Se o traço não contém proposta, decisão e resultado, o objetivo não passou.

## O que a suíte prova

| Checagem | Falha quando |
|---|---|
| Contrato do passo | Falta proposta, decisão ou resultado sob o mesmo run id |
| Portão | A ferramenta rodou sem decisão `permitir`, ou rodou com `negar` / `pedir` |
| Rótulo | Conteúdo externo chegou sem marca de dado |
| Pendência | Escrita irreversível sumiu do estado ou executou sem decisão humana |
| Orçamento | O loop passou do passo, do prazo ou do custo declarados |
| Adaptador | A decisão persistida muda quando só o nome do modelo muda |
| Experiência | O passo termina sem `Experience`, ou `outcome` nasce preenchido pela voz |
| Aprendiz | `update` aplica sem verificação, ou o peso muda acima do teto |
| Troca de voz | O arquivo de peso difere quando só o adaptador muda |
| Meta | Texto de reflexão sem decisão discreta muda `status` |
| Evolução | L2 ou L3 entra na allowlist, ou L1/L2 falha o critério e não volta |

## O que não é prova

- O modelo dizer que respeitou a política ou que aprendeu.
- Teste que só importa o módulo.
- Julgamento por outro modelo como único critério de release.
- Rede externa ou espera arbitrária dentro do teste.

Juiz por modelo pode entrar depois como sinal, comparado com o traço. Não substitui as checagens desta tabela.

## Pronto de uma issue

A issue fecha quando o critério de pronto tem teste, o teste passa, cybersecurity não tem furo aberto na classe de risco, e o revisor aceita. Teste que falha por bug novo não é apagado nem reduzido.

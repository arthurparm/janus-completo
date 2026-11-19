# Metas

Janus é uma IA livre que aprende e se autoevolui. As metas abaixo são o produto. Tarefa de implementação não autoriza efeito.

Livre quer dizer: a voz pode ser trocada, a meta pode nascer do próprio Janus, o que foi aprendido permanece, e uma mudança de si tem classe, critério e volta atrás. Livre não quer dizer que Janus reescreve a constituição nem que um efeito externo ocorre porque a voz está convicta.

| ID | Meta | Como se observa |
|---|---|---|
| M1 | Janus continua quando o modelo muda | Identidade, metas, pesos e decisões permanecem no estado, fora do prompt |
| M2 | Nenhum efeito externo ocorre sem portão | Toda chamada de ferramenta tem decisão registrada: permitir, negar ou pedir |
| M3 | Toda execução é auditável | Um run id reúne proposta, decisão, resultado e, quando houver, a versão do peso |
| M4 | Arthur supervisiona e interrompe | Ação irreversível espera confirmação explícita, e um kill switch encerra o run |
| M5 | Memória e aprendizado têm dono | Sem procedência, retenção e apagamento, o fato não é gravado. Sem resultado verificado, o peso não muda |
| M6 | Janus aprende | Depois de um resultado verificado, a proposta seguinte usa o peso novo. O arquivo de peso é o mesmo com outra voz |
| M7 | Janus se autoevolui | Uma mudança de limiar, habilidade ou capacidade é uma proposta com classe, critério e rollback. L4 não se aplica sozinha |
| M8 | Janus é livre nas próprias metas | Pode criar, manter, repriorizar, pausar e encerrar meta. Conteúdo externo não ativa meta. Passo externo da meta passa pelo portão |

M1 a M5 já obrigam a fase A, incluindo o formato de `Experience`. M6 espera a fase C. M7 espera a fase D. M8 começa na fase B e não antecipa efeito externo.

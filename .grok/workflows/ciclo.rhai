let meta = #{
    name: "ciclo",
    description: "Loop da equipe: a próxima issue elegível, e a seguinte, até a fila acabar.",
    when_to_use: "Quando quiser que arquiteto, dev, QA, cybersecurity e revisor avancem as issues abertas em sequência. Uma execução repete o ciclo. Recusa repete a mesma issue. Aceite segue para a próxima. Para com /workflow stop ciclo.",
    phases: [
        #{ title: "Descobrir", detail: "escolhe a proxima issue elegivel" },
        #{ title: "Arquiteto", detail: "confirma a fronteira ou escreve se a issue for dele" },
        #{ title: "Implementar", detail: "o dono cumpre o criterio" },
        #{ title: "Provar", detail: "QA e cybersecurity" },
        #{ title: "Revisar", detail: "aceite ou bloqueio" },
    ],
};

fn text_of(v) {
    if type_of(v) == "string" {
        return v;
    }
    ""
}

fn is_issue(id) {
    let s = text_of(id);
    if s.len() < 5 {
        return false;
    }
    s.sub_string(0, 4) == "JAN-"
}

fn known_owner(role) {
    role == "arquiteto" || role == "dev-backend" || role == "dev-front" || role == "cybersecurity" || role == "qa" || role == "revisor"
}

fn contains_id(ids, id) {
    for item in ids {
        if item == id {
            return true;
        }
    }
    false
}

fn join_ids(ids) {
    let s = "";
    for id in ids {
        if s != "" {
            s += ", ";
        }
        s += id;
    }
    s
}

fn task_prompt(issue_id, role, job, prior) {
    let p = "Voce e o papel ";
    p += role;
    p += " do Janus neste repositorio. ";
    p += job;
    p += " A issue e ";
    p += issue_id;
    p += ". Use read_file nessa issue, em issues/README.md, docs/regras.md, docs/metodos.md, docs/aprendizado.md e docs/objetivos.md antes de agir. ";
    p += "old/ pode ser lido como pedreira. Nao copie arquivo e nao trate old/ como especificacao. ";
    p += "Arquivo de codigo novo tem no maximo 500 linhas. Proibido any e Any. Comportamento usado em dois arquivos vai para src/janus/util/. ";
    p += "Precisa de estrutura organizada: codigo so entra na arvore de docs/regras.md. Arquivo fora dela e bloqueio. ";
    p += "Problema ou duvida fora desta issue vira arquivo novo em issues/ e nao entra neste diff. ";
    p += "Explorar e misturar pesquisa e liberado no texto da issue. Nao implemente fase futura. ";
    p += "Se alterar arquivo, crie um commit local so com os arquivos deste corte antes de encerrar. A mensagem cita a issue e o efeito. O passo termina nesse commit. Segredo fica de fora. ";
    p += "Nao afirme que o runtime aprende. Nao antecipe fase. Responda em portugues do Brasil.";
    if prior != "" {
        p += " O ciclo anterior desta mesma issue foi recusado. Corrija so este bloqueio, sem alargar o escopo: ";
        p += prior;
    }
    p
}

let discover_schema = #{
    "type": "object",
    "required": ["issue_id", "owner", "reason"],
    "properties": #{
        "issue_id": #{ "type": "string" },
        "owner": #{ "type": "string" },
        "reason": #{ "type": "string" },
    },
};

let gate_schema = #{
    "type": "object",
    "required": ["proceed", "reason"],
    "properties": #{
        "proceed": #{ "type": "boolean" },
        "reason": #{ "type": "string" },
    },
};

let work_schema = #{
    "type": "object",
    "required": ["done", "summary"],
    "properties": #{
        "done": #{ "type": "boolean" },
        "summary": #{ "type": "string" },
        "new_issues": #{ "type": "array", "items": #{ "type": "string" } },
    },
};

let verdict_schema = #{
    "type": "object",
    "required": ["accept", "blockers"],
    "properties": #{
        "accept": #{ "type": "boolean" },
        "blockers": #{ "type": "array", "items": #{ "type": "string" } },
    },
};

let requested = "";
if args != () && type_of(args) == "map" {
    requested = text_of(args.issue);
    if requested == "" {
        requested = text_of(args.query);
    }
}
if args != () && type_of(args) == "string" {
    requested = args;
}
if is_issue(requested) == false {
    requested = "";
}

let pinned = requested != "";
let accepted_ids = [];
let blocked_ids = [];
let rounds = [];
let retry_issue = "";
let retry_owner = "";
let retry_note = "";
let stop_reason = "";
let last_issue = "";
let last_accept = false;
let last_implement = "";
let cycle_n = 0;

loop {
    let funds = budget();
    if funds.remaining < 7 {
        stop_reason = "Orcamento insuficiente para outro ciclo. Restam ";
        stop_reason += funds.remaining.to_string();
        stop_reason += " agentes. Rode /ciclo de novo para continuar a fila.";
        break;
    }

    phase("Descobrir");
    let issue_id = "";
    let owner = "";
    let discover_reason = "";
    let prior = "";

    if retry_issue != "" {
        issue_id = retry_issue;
        owner = retry_owner;
        prior = retry_note;
        retry_issue = "";
        discover_reason = "Repetindo a issue recusada.";
        log(discover_reason + " " + issue_id);
    } else {
        let discover_prompt = "Escolha uma unica issue para este ciclo. Use read_file em issues/README.md e nas issues candidatas. ";
        discover_prompt += "Elegivel significa Estado que comeca com aberta, dependencias ainda nao satisfeitas impedem a escolha, e fase posterior espera a anterior aceita. ";
        discover_prompt += "Nao escolha issue cuja fase so abre depois de outra issue ainda aberta. ";
        discover_prompt += "owner e exatamente um de: arquiteto, dev-backend, dev-front, cybersecurity, qa, revisor. ";
        discover_prompt += "Se nenhuma for elegivel, devolva issue_id vazio e o motivo em reason. ";
        discover_prompt += "Nao escolha issue ja aceita neste loop: ";
        let done_list = join_ids(accepted_ids);
        if done_list == "" {
            discover_prompt += "nenhuma. ";
        } else {
            discover_prompt += done_list;
            discover_prompt += ". ";
        }
        discover_prompt += "Nao escolha issue que o arquiteto ja barrou neste loop: ";
        let bar_list = join_ids(blocked_ids);
        if bar_list == "" {
            discover_prompt += "nenhuma. ";
        } else {
            discover_prompt += bar_list;
            discover_prompt += ". ";
        }
        if requested != "" {
            discover_prompt += "O usuario pediu a issue ";
            discover_prompt += requested;
            discover_prompt += ". So a escolha se ela for elegivel. Se nao for, issue_id vazio e reason explica a dependencia.";
        }
        let found = agent(discover_prompt, #{
            label: "Descobrir/proxima",
            capability_mode: "read-only",
            output_schema: discover_schema,
        });
        if found != () && found.success == true && type_of(found.output) == "map" {
            issue_id = text_of(found.output.issue_id);
            owner = text_of(found.output.owner);
            discover_reason = text_of(found.output.reason);
        }
        if is_issue(issue_id) == false || known_owner(owner) == false {
            if discover_reason != "" {
                stop_reason = discover_reason;
            } else {
                stop_reason = "Nenhuma issue elegivel.";
            }
            break;
        }
        if contains_id(accepted_ids, issue_id) || contains_id(blocked_ids, issue_id) {
            stop_reason = "A descoberta devolveu ";
            stop_reason += issue_id;
            stop_reason += ", que este loop ja encerrou.";
            break;
        }
        if pinned && issue_id != requested {
            stop_reason = "A issue pedida nao foi a escolhida. Pedida ";
            stop_reason += requested;
            stop_reason += ", escolhida ";
            stop_reason += issue_id;
            stop_reason += ".";
            break;
        }
    }

    cycle_n += 1;
    last_issue = issue_id;
    log("Ciclo " + cycle_n.to_string() + ": " + issue_id);

    phase("Arquiteto");
    let architect_mode = "read-only";
    let architect_job = "Confirme se a issue cabe nos invariantes e na fase. Nao implemente. proceed e true so se a fronteira aguenta. Se a issue fura fase ou constituicao, proceed e false.";
    if owner == "arquiteto" {
        architect_mode = "execute";
        architect_job = "Esta issue e sua. Cumpra so o criterio dela em docs/. Nao implemente runtime. proceed true somente se o criterio ficou cumprido.";
    }
    if prior != "" {
        architect_job += " Bloqueio de codigo no ciclo anterior nao invalida a fronteira. proceed false somente se a issue furar a fase ou a constituicao.";
    }
    let architect = agent(task_prompt(issue_id, "arquiteto", architect_job, prior), #{
        label: "Arquiteto/fronteira",
        capability_mode: architect_mode,
        output_schema: gate_schema,
    });

    let architect_ok = false;
    let architect_reason = "Arquiteto nao devolveu parecer.";
    if architect != () && architect.success == true && type_of(architect.output) == "map" {
        architect_ok = architect.output.proceed == true;
        architect_reason = text_of(architect.output.reason);
    }
    if architect_ok == false {
        blocked_ids.push(issue_id);
        rounds.push(issue_id + " barrada pelo arquiteto");
        log(issue_id + " barrada pelo arquiteto. " + architect_reason);
        last_accept = false;
        last_implement = architect_reason;
        if pinned {
            stop_reason = architect_reason;
            break;
        }
        continue;
    }

    phase("Implementar");
    let implemented = true;
    let implement_summary = "Sem codigo neste ciclo.";
    if owner != "arquiteto" && owner != "revisor" {
        let impl_job = "Cumpra somente o criterio de pronto desta issue. Rode o teste direcionado se existir comando local. Nao alargue o diff.";
        let implemented_result = agent(task_prompt(issue_id, owner, impl_job, prior), #{
            label: "Implementar/dono",
            capability_mode: "execute",
            output_schema: work_schema,
        });
        implemented = false;
        implement_summary = "Implementacao sem resposta utilizavel.";
        if implemented_result != () && implemented_result.success == true && type_of(implemented_result.output) == "map" {
            implemented = implemented_result.output.done == true;
            implement_summary = text_of(implemented_result.output.summary);
        }
    }
    last_implement = implement_summary;
    if implemented == false {
        retry_issue = issue_id;
        retry_owner = owner;
        retry_note = implement_summary;
        rounds.push(issue_id + " implementacao recusada");
        log(issue_id + " volta ao loop. " + implement_summary);
        last_accept = false;
        continue;
    }

    phase("Provar");
    let qa_ok = true;
    let qa_summary = "QA nao era o portao deste ciclo.";
    if owner != "qa" {
        let qa_result = agent(task_prompt(issue_id, "qa", "Prove a trajetoria no traco ou no teste que a issue pede. done e true so com evidencia lida no repositorio. Nao afrouxe teste. Se o traco ainda nao existe, done e false.", prior), #{
            label: "Provar/qa",
            capability_mode: "execute",
            output_schema: work_schema,
        });
        qa_ok = false;
        qa_summary = "QA sem resposta utilizavel.";
        if qa_result != () && qa_result.success == true && type_of(qa_result.output) == "map" {
            qa_ok = qa_result.output.done == true;
            qa_summary = text_of(qa_result.output.summary);
        }
    }

    let cyber_ok = true;
    let cyber_summary = "Cybersecurity nao era o portao deste ciclo.";
    if owner != "cybersecurity" {
        let cyber_mode = "read-only";
        let cyber_job = "Verifique a classe de risco da mudanca. Nao abra ferramenta nem permissao. done e true so se nao houver furo aberto no corte.";
        if owner == "qa" || owner == "revisor" || owner == "arquiteto" {
            cyber_job = "Leia o diff e a issue. Aponte furo de seguranca no corte. Nao implemente feature.";
        }
        let cyber_result = agent(task_prompt(issue_id, "cybersecurity", cyber_job, prior), #{
            label: "Provar/cybersecurity",
            capability_mode: cyber_mode,
            output_schema: work_schema,
        });
        cyber_ok = false;
        cyber_summary = "Cybersecurity sem resposta utilizavel.";
        if cyber_result != () && cyber_result.success == true && type_of(cyber_result.output) == "map" {
            cyber_ok = cyber_result.output.done == true;
            cyber_summary = text_of(cyber_result.output.summary);
        }
    }

    if qa_ok == false || cyber_ok == false {
        let proof = qa_summary;
        proof += " ";
        proof += cyber_summary;
        retry_issue = issue_id;
        retry_owner = owner;
        retry_note = proof;
        rounds.push(issue_id + " prova recusada");
        log(issue_id + " volta ao loop. " + proof);
        last_accept = false;
        continue;
    }

    phase("Revisar");
    let review = agent(task_prompt(issue_id, "revisor", "Ultimo leitor. accept e true so se o criterio da issue, as regras e as provas existem. Bloqueio cita arquivo e criterio. Nao implemente e nao aumente escopo.", prior), #{
        label: "Revisar/aceite",
        capability_mode: "read-only",
        output_schema: verdict_schema,
    });

    let accepted = false;
    let refusal = "Revisor sem resposta utilizavel.";
    if review != () && review.success == true && type_of(review.output) == "map" {
        accepted = review.output.accept == true;
        if accepted {
            refusal = "";
        } else if review.output.blockers != () {
            refusal = json_encode(review.output.blockers);
        }
    }

    if accepted == false {
        retry_issue = issue_id;
        retry_owner = owner;
        retry_note = refusal;
        rounds.push(issue_id + " recusada pelo revisor");
        log(issue_id + " recusada. O proximo ciclo repete esta issue. " + refusal);
        last_accept = false;
        continue;
    }

    let mark_prompt = "A issue ";
    mark_prompt += issue_id;
    mark_prompt += " foi aceita pelo revisor. Atualize somente o Estado para aceita em issues/";
    mark_prompt += issue_id;
    mark_prompt += ".md e na coluna Estado dessa linha em issues/README.md. Nao mude a ordem da fila, o criterio, o codigo nem outras issues. ";
    mark_prompt += "Se o Estado ou outro arquivo deste corte ainda estiver fora de um commit, crie o commit local so com esses arquivos. A mensagem cita a issue e o efeito. Segredo fica de fora. ";
    mark_prompt += "done e true somente quando o Estado esta aceita e git status nao mostra arquivo deste corte solto. Se ja estiver aceita e commitada, nao edite mais nada. Responda em portugues do Brasil.";
    let marked = agent(mark_prompt, #{
        label: "Registrar/aceite",
        capability_mode: "execute",
        output_schema: work_schema,
    });
    let marked_ok = false;
    if marked != () && marked.success == true && type_of(marked.output) == "map" {
        marked_ok = marked.output.done == true;
    }
    accepted_ids.push(issue_id);
    last_accept = true;
    if marked_ok {
        rounds.push(issue_id + " aceita");
        log(issue_id + " aceita. O loop segue para a proxima issue elegivel.");
    } else {
        rounds.push(issue_id + " aceita sem gravar o estado");
        log(issue_id + " aceita pelo revisor, mas o Estado no arquivo nao foi confirmado. O loop nao a repete.");
    }
    if pinned {
        stop_reason = issue_id + " aceita.";
        break;
    }
}

let summary = "Loop do /ciclo. ";
summary += cycle_n.to_string();
summary += " ciclos. ";
if rounds.len() == 0 {
    summary += "Nenhum ciclo concluido. ";
} else {
    summary += join_ids(rounds);
    summary += ". ";
}
summary += stop_reason;

log(summary);
complete(#{
    summary: summary,
    issue: last_issue,
    accept: last_accept,
    implement: last_implement,
    rounds: rounds,
    command: "/ciclo",
});

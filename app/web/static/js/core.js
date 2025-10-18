(function(){
  const CIRCUMFERENCE = 2 * Math.PI * 60; // r=60 matches SVG
  const progressEl = document.getElementById('core-progress');
  const tooltipEl = document.getElementById('tooltip');
  const heroCore = document.querySelector('.hero-core');

  const nodes = {
    memory: document.getElementById('node-memory'),
    knowledge: document.getElementById('node-knowledge'),
    agent: document.getElementById('node-agent'),
    task: document.getElementById('node-task'),
  };
  const lines = {
    memory: document.getElementById('line-memory'),
    knowledge: document.getElementById('line-knowledge'),
    agent: document.getElementById('line-agent'),
    task: document.getElementById('line-task'),
  };

  function clamp01(v){ return Math.max(0, Math.min(1, v)); }
  function setProgress(percent){
    const p = clamp01(percent);
    const offset = CIRCUMFERENCE * (1 - p);
    progressEl.style.strokeDasharray = String(CIRCUMFERENCE);
    progressEl.style.strokeDashoffset = String(offset);
  }

  function setActive(name, active){
    const line = lines[name];
    const node = nodes[name];
    if (!line || !node) return;
    line.classList.toggle('active', !!active);
    node.classList.toggle('active', !!active);
  }

  function setNodeHealth(name, status){
    const node = nodes[name];
    if (!node) return;
    node.classList.remove('status-success','status-warning','status-error');
    const s = (status||'').toLowerCase();
    if (s === 'ok' || s === 'healthy' || s === 'success') node.classList.add('status-success');
    else if (s === 'degraded' || s === 'warning') node.classList.add('status-warning');
    else if (s === 'error' || s === 'unhealthy' || s === 'fail' || s === 'down') node.classList.add('status-error');
  }

  function heuristicHealth(summary){
    const agents = (summary?.multi_agent?.active_agents) ?? 0;
    const tasks = (summary?.multi_agent?.workspace_tasks) ?? 0;
    const artifacts = (summary?.multi_agent?.workspace_artifacts) ?? 0;
    const llmCb = summary?.llm?.circuit_breakers || {};
    const cbOpen = Object.values(llmCb).some(v => v.state && String(v.state).toLowerCase() !== 'closed');
    const h = {};
    h.agent = agents > 0 ? 'ok' : 'error';
    h.task = tasks > 20 ? 'error' : (tasks > 10 ? 'degraded' : 'ok');
    h.memory = artifacts === 0 ? 'error' : (artifacts <= 5 ? 'degraded' : 'ok');
    h.knowledge = cbOpen ? 'degraded' : (artifacts > 5 ? 'ok' : 'degraded');
    return h;
  }

  let lastSummary = null;
  let lastHealth = null;

  function applyHealthFromServices(services){
    if (!Array.isArray(services)) return;
    const map = {};
    services.forEach(svc => { map[(svc.key||'').toLowerCase()] = (svc.status||'').toLowerCase(); });
    if (map.agent) setNodeHealth('agent', map.agent);
    if (map.knowledge) setNodeHealth('knowledge', map.knowledge);
    if (map.memory) setNodeHealth('memory', map.memory);
    // Não há chave explícita para 'task' no serviço; mantém heurística pelo summary
  }

  async function fetchServiceHealth(){
    try {
      const res = await fetch('/api/v1/system/health/services');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const j = await res.json();
      lastHealth = j.services || j;
      applyHealthFromServices(lastHealth);
    } catch (e) {
      // mantém último ou heurística do summary
      if (lastSummary) {
        const h = heuristicHealth(lastSummary);
        setNodeHealth('agent', h.agent);
        setNodeHealth('task', h.task);
        setNodeHealth('memory', h.memory);
        setNodeHealth('knowledge', h.knowledge);
      }
    }
  }

  function updateCore(summary){
    const activity = computeActivity(summary);
    setProgress(activity);

    const agents = (summary?.multi_agent?.active_agents) ?? 0;
    const tasks = (summary?.multi_agent?.workspace_tasks) ?? 0;
    const artifacts = (summary?.multi_agent?.workspace_artifacts) ?? 0;
    const llmCb = summary?.llm?.circuit_breakers || {};
    const cbOpen = Object.values(llmCb).some(v => v.state && String(v.state).toLowerCase() !== 'closed');

    const isAgentActive = agents > 0;
    const isTaskActive = tasks > 0;
    const isMemoryActive = artifacts > 0;
    const isKnowledgeActive = (artifacts > 5) || cbOpen;

    setActive('agent', isAgentActive);
    setActive('task', isTaskActive);
    setActive('memory', isMemoryActive);
    setActive('knowledge', isKnowledgeActive);

    lines.agent && lines.agent.classList.toggle('particles', !!isAgentActive);
    lines.task && lines.task.classList.toggle('particles', !!isTaskActive);
    lines.memory && lines.memory.classList.toggle('particles', !!isMemoryActive);
    lines.knowledge && lines.knowledge.classList.toggle('particles', !!isKnowledgeActive);

    // Atualiza saúde: usa dados do serviço quando disponíveis, senão heurística
    if (lastHealth) applyHealthFromServices(lastHealth);
    else {
      const h = heuristicHealth(summary);
      setNodeHealth('agent', h.agent);
      setNodeHealth('task', h.task);
      setNodeHealth('memory', h.memory);
      setNodeHealth('knowledge', h.knowledge);
    }
  }

  async function fetchSummary(){
    try {
      const res = await fetch('/api/v1/observability/metrics/summary');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      lastSummary = data;
      updateCore(data);
    } catch (e) {
      lastSummary = mockSummary(lastSummary);
      updateCore(lastSummary);
    }
  }

  function positionTooltip(svgX, svgY, html){
    if (!heroCore) return;
    // Usar coordenadas relativas ao container .hero-core, não ao viewport
    const w = heroCore.clientWidth;
    const h = heroCore.clientHeight;
    const sx = w / 600; // viewBox width
    const sy = h / 360; // viewBox height
    const left = svgX * sx;
    const top = svgY * sy;
    tooltipEl.style.left = `${left}px`;
    tooltipEl.style.top = `${top}px`;
    tooltipEl.innerHTML = html;
    tooltipEl.classList.add('show');
  }
  function hideTooltip(){ tooltipEl.classList.remove('show'); }

  function mockSummary(prev){
    const jitter = (x, j) => Math.max(0, x + (Math.random() * j * 2 - j));
    const base = prev || {
      llm: { cached_llms: Math.floor(Math.random()*5), circuit_breakers: {} },
      multi_agent: { active_agents: Math.floor(Math.random()*3)+1, workspace_tasks: Math.floor(Math.random()*8), workspace_artifacts: Math.floor(Math.random()*20) },
      poison_pills: { total_quarantined: 0 }
    };
    return {
      llm: { cached_llms: Math.round(jitter(base.llm.cached_llms, 1)), circuit_breakers: base.llm.circuit_breakers },
      multi_agent: {
        active_agents: Math.round(jitter(base.multi_agent.active_agents, 1)),
        workspace_tasks: Math.round(jitter(base.multi_agent.workspace_tasks, 2)),
        workspace_artifacts: Math.round(jitter(base.multi_agent.workspace_artifacts, 3))
      },
      poison_pills: base.poison_pills
    };
  }

  function computeActivity(summary){
    const agents = (summary?.multi_agent?.active_agents) ?? 0;
    const tasks = (summary?.multi_agent?.workspace_tasks) ?? 0;
    const llmCached = (summary?.llm?.cached_llms) ?? 0;
    const agentsNorm = clamp01(agents / 10);
    const tasksNorm = clamp01(tasks / 20);
    const llmNorm = clamp01(llmCached / 10);
    return clamp01(0.5 * agentsNorm + 0.3 * tasksNorm + 0.2 * llmNorm);
  }

  // Node tooltips
  const TOOLTIP_POS = {
    memory: { x: 150, y: 60 },
    knowledge: { x: 450, y: 60 },
    agent: { x: 150, y: 300 },
    task: { x: 450, y: 300 },
  };
  function bindTooltip(name, getHtml){
    const node = nodes[name];
    const line = lines[name];
    if (!node) return;
    node.addEventListener('mouseenter', () => {
      const pos = TOOLTIP_POS[name];
      const html = getHtml(lastSummary);
      positionTooltip(pos.x, pos.y, html);
      // reforço visual: realça a linha conectada
      if (line) line.classList.add('active');
    });
    node.addEventListener('mouseleave', () => {
      hideTooltip();
      if (line) line.classList.remove('active');
    });
  }

  bindTooltip('agent', (s) => `Agentes Ativos: <b>${(s?.multi_agent?.active_agents ?? '—')}</b>`);
  bindTooltip('task', (s) => `Tarefas na Fila: <b>${(s?.multi_agent?.workspace_tasks ?? '—')}</b>`);
  bindTooltip('memory', (s) => `Artefatos no Workspace: <b>${(s?.multi_agent?.workspace_artifacts ?? '—')}</b>`);
  bindTooltip('knowledge', (s) => {
    const cb = s?.llm?.circuit_breakers || {}; const opened = Object.values(cb).filter(v => v.state && String(v.state).toLowerCase() !== 'closed').length;
    return `Circuit Breakers Abertos: <b>${opened}</b>`;
  });

  // Initialize
  setProgress(0);
  fetchSummary();
  fetchServiceHealth();
  setInterval(fetchSummary, 4000);
  setInterval(fetchServiceHealth, 6000);
})();
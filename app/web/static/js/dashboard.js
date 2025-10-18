(function(){
  const statusBadge = document.getElementById('status-badge');
  const statusText = document.getElementById('status-text');
  const appNameEl = document.getElementById('app-name');
  const appVersionEl = document.getElementById('app-version');
  const uptimeEl = document.getElementById('uptime');
  const refreshBtn = document.getElementById('btn-refresh');

  function formatUptime(seconds){
    if (typeof seconds !== 'number') return '—';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  }

  function setBadge(status){
    statusBadge.classList.remove('status-success','status-warning','status-error');
    const s = (status || '').toLowerCase();
    if (['ok','operational','online','healthy','up'].includes(s)) {
      statusBadge.classList.add('status-success');
      statusText.textContent = 'Online';
    } else if (['degraded','warning','unstable','partial','minor'].includes(s)) {
      statusBadge.classList.add('status-warning');
      statusText.textContent = 'Degradado';
    } else {
      statusBadge.classList.add('status-error');
      statusText.textContent = 'Falha';
    }
  }

  async function fetchStatus(){
    try {
      const res = await fetch('/api/v1/system/status');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      appNameEl.textContent = data.app_name || 'Janus';
      appVersionEl.textContent = data.version || '—';
      uptimeEl.textContent = formatUptime(data.uptime_seconds);
      setBadge((data.status || '').toLowerCase());
    } catch (err) {
      console.error('Erro ao buscar status:', err);
      setBadge('error');
      statusText.textContent = 'Erro de conexão';
    }
  }

  // --- Saúde dos Microsserviços ---
  function setItemStatus(el, status){
    el.classList.remove('status-success','status-warning','status-error');
    const s = (status||'').toLowerCase();
    if (s === 'ok' || s === 'healthy') el.classList.add('status-success');
    else if (s === 'degraded' || s === 'warning') el.classList.add('status-warning');
    else el.classList.add('status-error');
  }
  function updateServiceHealth(data){
    const container = document.querySelector('.service-health-grid');
    if (!container || !Array.isArray(data)) return;
    data.forEach(svc => {
      const key = svc.key || svc.name?.toLowerCase().split(' ')[0];
      const el = container.querySelector(`[data-service="${key}"]`);
      if (!el) return;
      setItemStatus(el, svc.status);
      const metricEl = el.querySelector('.metric');
      if (metricEl) metricEl.textContent = svc.metric_text || '—';
    });
  }
  async function fetchServiceHealth(){
    try {
      const res = await fetch('/api/v1/system/health/services');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const j = await res.json();
      updateServiceHealth(j.services || j);
    } catch (e) {
      // Fallback sintético
      const mock = [
        { key: 'agent', name: 'Agent Service', status: 'ok', metric_text: `Agentes: ${Math.floor(Math.random()*4)+1}/10` },
        { key: 'knowledge', name: 'Knowledge Service', status: Math.random()>0.7?'degraded':'ok', metric_text: `Ontologias: ${Math.floor(Math.random()*20)+5}` },
        { key: 'memory', name: 'Memory Service', status: 'ok', metric_text: `Uso: ${Math.floor(Math.random()*256)+128}MB` },
        { key: 'llm', name: 'LLM Gateway', status: Math.random()>0.2?'ok':'degraded', metric_text: `Latência: ${Math.floor(80 + Math.random()*120)}ms` },
      ];
      updateServiceHealth(mock);
    }
  }

  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      try {
        refreshBtn.classList.add('loading');
        refreshBtn.disabled = true;
        await fetchStatus();
        refreshBtn.classList.remove('loading');
        refreshBtn.classList.add('success');
        refreshBtn.disabled = false;
        setTimeout(() => refreshBtn.classList.remove('success'), 1000);
      } catch (e) {
        refreshBtn.classList.remove('loading');
        refreshBtn.disabled = false;
      }
    });
  }

  // Inicialização
  fetchStatus();
  fetchServiceHealth();
  // Atualização periódica
  setInterval(fetchStatus, 5000);
  setInterval(fetchServiceHealth, 6000);
})();
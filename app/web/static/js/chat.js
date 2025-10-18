// Janus Chat UI Logic — Diálogo Aumentado
(function(){
  const messagesEl = document.querySelector('.messages');
  const inputEl = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send');
  const contextPanel = document.getElementById('context-panel');
  const sourcesEls = Array.from(document.querySelectorAll('.knowledge-sources li'));
  const intentTagsEl = document.getElementById('intent-tags');

  let conversationId = null;
  let sourcesTimer = null;

  // Helpers
  function scrollMessagesToEnd(){
    try { messagesEl?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'end' }); } catch {}
  }
  function nowLabel(){ return 'agora'; }
  function sanitize(s){ return String(s || '').slice(0, 10000); }

  function addUserMessage(text){
    const wrap = document.createElement('div');
    wrap.className = 'msg user';
    wrap.innerHTML = `<div class="meta">Você • ${nowLabel()}</div><div class="content"></div>`;
    wrap.querySelector('.content').textContent = sanitize(text);
    messagesEl.appendChild(wrap);
    scrollMessagesToEnd();
    return wrap;
  }
  function addAIProcessing(){
    const wrap = document.createElement('div');
    wrap.className = 'msg ai processing';
    wrap.innerHTML = `<div class="meta">Janus • processando</div><div class="content">Analisando consulta...</div>`;
    messagesEl.appendChild(wrap);
    scrollMessagesToEnd();
    return wrap;
  }
  function setGenerating(bubble, placeholder){
    bubble.classList.remove('processing');
    bubble.classList.add('generating');
    const contentEl = bubble.querySelector('.content');
    if (placeholder) {
      contentEl.classList.add('typewriter');
      contentEl.textContent = placeholder;
    } else {
      contentEl.classList.remove('typewriter');
    }
    bubble.querySelector('.meta').textContent = 'Janus • gerando';
  }
  function setGeneratingText(bubble, text){
    const contentEl = bubble.querySelector('.content');
    contentEl.classList.remove('typewriter');
    contentEl.textContent = text;
  }
  function setComplete(bubble, text){
    bubble.classList.remove('generating');
    bubble.classList.remove('processing');
    bubble.classList.add('complete');
    bubble.querySelector('.meta').textContent = 'Janus • completo';
    bubble.querySelector('.content').textContent = sanitize(text);
    scrollMessagesToEnd();
  }

  function activateContext(){
    // CSS :has() já aumenta opacidade com .processing, mas simulamos atividade das fontes
    let idx = 0;
    sourcesTimer = setInterval(() => {
      sourcesEls.forEach(el => el.classList.remove('active'));
      // ativar 1–2 itens
      const available = [...sourcesEls];
      const pick1 = available.splice(Math.floor(Math.random()*available.length), 1)[0];
      const pick2 = available.length ? available[Math.floor(Math.random()*available.length)] : null;
      if (pick1) pick1.classList.add('active');
      if (pick2 && Math.random() > 0.5) pick2.classList.add('active');
      idx++;
    }, 500);
  }
  function deactivateContext(){
    if (sourcesTimer) { clearInterval(sourcesTimer); sourcesTimer = null; }
    sourcesEls.forEach(el => el.classList.remove('active'));
  }

  async function startConversation(){
    try {
      const res = await fetch('/api/v1/chat/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ persona: null }) });
      if (!res.ok) throw new Error('start failed');
      const data = await res.json();
      conversationId = data.conversation_id;
      return conversationId;
    } catch (e) {
      console.warn('Falha ao iniciar conversa, usando fallback local:', e);
      conversationId = conversationId || 'local';
      return conversationId;
    }
  }

  function safeParse(str){ try { return JSON.parse(str); } catch { return null; } }

  function streamChat(cid, message, aiBubble){
    return new Promise((resolve, reject) => {
      const url = `/api/v1/chat/stream/${encodeURIComponent(cid)}?message=${encodeURIComponent(message)}&role=orchestrator&priority=fast_and_cheap`;
      const es = new EventSource(url);
      let finalText = '';
      let started = false;

      const cleanup = () => { try { es.close(); } catch {} };

      es.addEventListener('start', () => { started = true; });
      es.addEventListener('ack', (ev) => {
        const data = safeParse(ev.data);
        if (data?.conversation_id) { conversationId = data.conversation_id; }
      });
      es.addEventListener('partial', (ev) => {
        const data = safeParse(ev.data);
        const chunk = (data && data.text) ? String(data.text) : '';
        if (!aiBubble.classList.contains('generating')) {
          setGenerating(aiBubble);
        }
        finalText += chunk;
        setGeneratingText(aiBubble, finalText);
      });
      es.addEventListener('done', () => {
        cleanup();
        setComplete(aiBubble, finalText || '');
        deactivateContext();
        resolve(finalText);
      });
      es.addEventListener('error', (ev) => {
        console.warn('SSE erro, encerrando stream:', ev);
        cleanup();
        deactivateContext();
        reject(new Error('stream-error'));
      });

      // segurança: timeout
      setTimeout(() => { cleanup(); resolve(finalText); }, 30000);
    });
  }

  async function sendMessageFlow(text){
    const aiBubble = addAIProcessing();
    activateContext();

    // tentativa com SSE streaming; fallback para simulação + POST
    try {
      if (!conversationId || conversationId === 'local') await startConversation();
      await streamChat(conversationId, text, aiBubble);
    } catch (err) {
      // Fallback: simular
      console.warn('Fallback de resposta simulada:', err);
      setTimeout(() => setGenerating(aiBubble, 'Estou analisando seu pedido e preparando uma resposta...'), 2000);
      setTimeout(() => { setComplete(aiBubble, 'Resposta gerada (simulação). Posso ajudar com mais detalhes?'); deactivateContext(); }, 5000);
    }
  }

  // Intent tags em tempo real
  function updateIntentTags(text){
    const tags = [];
    const lower = String(text || '').toLowerCase();
    if (lower.includes('código') || lower.includes('.py')) tags.push('Escopo: Análise de Código');
    if (lower.includes('como') || lower.includes('por que') || lower.includes('por quê')) tags.push('Intenção: Pergunta');
    if (!tags.length && lower.trim().length > 0) tags.push('Intenção: consulta');
    intentTagsEl.innerHTML = tags.map(t => `<span class="tag">${t}</span>`).join('');
  }

  // Eventos
  if (inputEl) {
    inputEl.addEventListener('keyup', () => updateIntentTags(inputEl.value));
  }
  if (sendBtn) {
    sendBtn.addEventListener('click', async () => {
      const text = inputEl?.value?.trim();
      if (!text) return;
      addUserMessage(text);
      inputEl.value = '';
      updateIntentTags('');
      await sendMessageFlow(text);
    });
  }

  // Inicialização
  startConversation();
})();
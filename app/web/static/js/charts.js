(function(){
  const latencyCanvas = document.getElementById('chart-latency');
  const errorCanvas = document.getElementById('chart-error');
  const memoryCanvas = document.getElementById('chart-memory');
  if (!latencyCanvas || !errorCanvas || !memoryCanvas) return;

  function cssVar(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  const palette = {
    primary: cssVar('--primary') || '#007BFF',
    success: cssVar('--success') || '#28A745',
    warning: cssVar('--warning') || '#FFC107',
    error: cssVar('--error') || '#DC3545',
    text: cssVar('--text-primary') || '#FFFFFF',
    muted: cssVar('--muted') || '#9A9A9A',
    border: cssVar('--border') || '#2A2A2A'
  };

  function hexToRgba(hex, a){
    const h = hex.replace('#','');
    const bigint = parseInt(h.length===3 ? h.split('').map(x=>x+x).join('') : h, 16);
    const r = (bigint >> 16) & 255, g = (bigint >> 8) & 255, b = bigint & 255;
    return `rgba(${r},${g},${b},${a})`;
  }

  function setupCanvas(canvas){
    const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1));
    const ctx = canvas.getContext('2d');
    const w = canvas.clientWidth || canvas.width; const h = canvas.clientHeight || canvas.height;
    canvas.width = w * dpr; canvas.height = h * dpr; canvas.style.width = `${w}px`; canvas.style.height = `${h}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { canvas, ctx, w, h };
  }

  function easeOutCubic(t){ return 1 - Math.pow(1 - t, 3); }

  class LineChart{
    constructor(canvas, color){
      const { ctx, w, h } = setupCanvas(canvas);
      this.canvas = canvas; this.ctx = ctx; this.w = w; this.h = h; this.color = color;
      this.padding = { top: 12, right: 12, bottom: 18, left: 28 };
      this.gridLines = 5; this.lastAnim = null; this.hoverIndex = null; this.points = [];
    }
    setData(points){
      this.points = points.map((y, i) => ({ x: i, y }));
      this.drawFrame(1);
      return this;
    }
    clear(){ this.ctx.clearRect(0,0,this.w,this.h); }
    _scales(){
      const N = this.points.length || 2;
      const xs = this.points.map(p=>p.x);
      const ys = this.points.map(p=>p.y);
      const xMin = 0, xMax = Math.max(...xs, 1);
      const minY = Math.min(...ys, 0), maxY = Math.max(...ys, 1);
      const pad = Math.max(1e-3, (maxY-minY) * 0.15);
      const yMin = minY - pad; const yMax = maxY + pad;
      const innerW = this.w - this.padding.left - this.padding.right;
      const innerH = this.h - this.padding.top - this.padding.bottom;
      const xScale = v => this.padding.left + (v - xMin) / (xMax - xMin) * innerW;
      const yScale = v => this.h - this.padding.bottom - (v - yMin) / (yMax - yMin) * innerH;
      return { xScale, yScale, innerW, innerH };
    }
    _drawAxes(scales){
      const { ctx } = this;
      ctx.save();
      ctx.strokeStyle = hexToRgba(palette.text, 0.08);
      ctx.fillStyle = palette.muted;
      ctx.lineWidth = 1;
      const steps = this.gridLines;
      for (let i=0; i<=steps; i++){
        const y = this.padding.top + i * (scales.innerH / steps);
        ctx.beginPath(); ctx.moveTo(this.padding.left, y); ctx.lineTo(this.w - this.padding.right, y); ctx.stroke();
      }
      ctx.restore();
    }
    _drawLine(scales, progress){
      const { ctx } = this;
      ctx.save();
      ctx.strokeStyle = hexToRgba(this.color, 0.9);
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i=0; i<this.points.length; i++){
        const p = this.points[i];
        const x = scales.xScale(p.x);
        const y = scales.yScale(p.y);
        const t = i / Math.max(1, this.points.length - 1);
        if (t <= progress) {
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
      // Hover glow on nearest point
      if (this.hoverIndex != null){
        const hp = this.points[this.hoverIndex];
        const hx = scales.xScale(hp.x), hy = scales.yScale(hp.y);
        ctx.fillStyle = hexToRgba(this.color, 0.35);
        ctx.beginPath(); ctx.arc(hx, hy, 4.5, 0, Math.PI*2); ctx.fill();
      }
      // Last point glow
      const last = this.points[this.points.length-1];
      if (last){
        const lx = scales.xScale(last.x), ly = scales.yScale(last.y);
        ctx.fillStyle = hexToRgba(this.color, 0.25);
        ctx.beginPath(); ctx.arc(lx, ly, 3.5, 0, Math.PI*2); ctx.fill();
      }
      ctx.restore();
    }
    drawFrame(progress){
      this.clear();
      const scales = this._scales();
      this._drawAxes(scales);
      this._drawLine(scales, progress);
    }
    animateDraw(duration=1000){
      const start = performance.now();
      const step = (now)=>{
        const t = Math.min(1, (now - start) / duration);
        const p = easeOutCubic(t);
        this.drawFrame(p);
        if (t < 1) this.lastAnim = requestAnimationFrame(step);
      };
      if (this.lastAnim) cancelAnimationFrame(this.lastAnim);
      this.lastAnim = requestAnimationFrame(step);
      return duration;
    }
    _nearestPoint(scales, x, y){
      let best = { idx: null, dist: Infinity };
      for (let i=0;i<this.points.length;i++){
        const p = this.points[i];
        const px = scales.xScale(p.x), py = scales.yScale(p.y);
        const dx = px - x, dy = py - y;
        const d = Math.sqrt(dx*dx + dy*dy);
        if (d < best.dist){ best = { idx: i, dist: d }; }
      }
      return best.dist <= 12 ? best.idx : null;
    }
  }

  const latencyChart = new LineChart(latencyCanvas, palette.primary);
  const errorChart = new LineChart(errorCanvas, palette.error);
  const memoryChart = new LineChart(memoryCanvas, palette.success);

  function synthLatencySeries(latest, p95){
    const N = 30; const series = [];
    const base = Math.max(0.05, latest || 0.5);
    const peak = Math.max(base*1.2, p95 || base*2);
    for(let i=0;i<N;i++){
      const t = i/(N-1);
      const decay = Math.exp(-3*t);
      const val = base + (peak - base) * (1 - decay) + (Math.random()-0.5)*base*0.05;
      series.push(Number(val.toFixed(3)));
    }
    return series;
  }
  function synthErrorSeries(avg){
    const N = 30; const series = []; const base = Math.max(0, avg || 0.1);
    for(let i=0;i<N;i++){
      series.push(Number((base + (Math.random()-0.5) * base * 0.2).toFixed(3)));
    }
    return series;
  }
  function synthMemorySeries(latestMb, maxMb){
    const N = 30; const series = []; const base = Math.max(64, latestMb || 256);
    const ceiling = Math.max(base, maxMb || base*1.25);
    let drift = (Math.random() * 0.06) - 0.03;
    for(let i=0;i<N;i++){
      drift += (Math.random()*0.02 - 0.01);
      const val = Math.min(ceiling, Math.max(64, base * (1 + drift)));
      series.push(Number(val.toFixed(2)));
    }
    return series;
  }

  function refreshButtonState(loading, success){
    const btn = document.getElementById('metrics-refresh');
    if (!btn) return;
    btn.classList.toggle('loading', !!loading);
    btn.classList.toggle('success', !!success);
    btn.disabled = !!loading;
    if (loading) btn.textContent = 'Atualizando...';
    else if (success) { btn.textContent = 'Concluído'; setTimeout(()=>{ btn.classList.remove('success'); btn.textContent = 'Atualizar métricas'; }, 1000); }
    else btn.textContent = 'Atualizar métricas';
  }

  function markLoading(on){
    [latencyCanvas, errorCanvas, memoryCanvas].forEach(c => c.classList.toggle('loading', !!on));
  }

  async function fetchAnalyze(){
    try {
      markLoading(true);
      const res = await fetch('/api/v1/optimization/analyze?analysis_type=performance&detailed=false', { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const j = await res.json();
      const t = j.trend || {}; const snap = j.metrics_snapshot || {}; const series = j.series || {};
      const dur = 1200;
      // Extrai séries reais do sistema
      const latencySec = Array.isArray(series.avg_response_time) ? series.avg_response_time : [snap.avg_response_time ?? t.avg_response_time_latest ?? 0];
      const errorFrac = Array.isArray(series.error_rate) ? series.error_rate : [snap.error_rate ?? t.error_rate_avg ?? 0];
      const memoryMb = Array.isArray(series.memory_usage_mb) ? series.memory_usage_mb : [snap.memory_usage_mb ?? t.memory_usage_latest_mb ?? 0];
      // Converte para unidades de exibição
      const latencyMs = latencySec.map(v => Math.round((v || 0) * 1000));
      const errorPct = errorFrac.map(v => Number(((v || 0) * 100).toFixed(2)));
      const memoryData = memoryMb.map(v => Number((v || 0).toFixed(2)));
      // Atualiza valores numéricos
      const lv = document.getElementById('latency-value');
      if (lv && latencyMs.length) lv.textContent = `${latencyMs[latencyMs.length - 1]} ms`;
      const ev = document.getElementById('error-value');
      if (ev && errorPct.length) ev.textContent = `${errorPct[errorPct.length - 1]} %`;
      const mv = document.getElementById('memory-value');
      if (mv && memoryData.length) mv.textContent = `${memoryData[memoryData.length - 1]} MB`;
      // Desenha gráficos com dados reais
      latencyChart.setData(latencyMs).animateDraw(dur);
      errorChart.setData(errorPct).animateDraw(dur);
      memoryChart.setData(memoryData).animateDraw(dur);
      setTimeout(()=>markLoading(false), dur);
    } catch(e) {
      // Fallback: usar endpoint de saúde para números, sem dados sintéticos
      try {
        const res2 = await fetch('/api/v1/optimization/health');
        if (res2.ok) {
          const h = await res2.json();
          const lv = document.getElementById('latency-value');
          if (lv) lv.textContent = `${Math.round((h.avg_response_time || 0) * 1000)} ms`;
          const ev = document.getElementById('error-value');
          if (ev) ev.textContent = `${Number(((h.error_rate || 0) * 100).toFixed(2))} %`;
          const mv = document.getElementById('memory-value');
          if (mv) mv.textContent = `${Number((h.memory_usage_mb || 0).toFixed(2))} MB`;
        }
      } catch {}
      markLoading(false);
    }
  }

  document.getElementById('metrics-refresh')?.addEventListener('click', async () => {
    refreshButtonState(true, false);
    await fetchAnalyze();
    refreshButtonState(false, true);
  });

  // Hover interactions: glow on nearest point
  function attachHover(chart){
    const onMove = (evt)=>{
      const rect = chart.canvas.getBoundingClientRect();
      const x = evt.clientX - rect.left;
      const y = evt.clientY - rect.top;
      const scales = chart._scales();
      chart.hoverIndex = chart._nearestPoint(scales, x, y);
      chart.drawFrame(1);
    };
    const onLeave = ()=>{ chart.hoverIndex = null; chart.drawFrame(1); };
    chart.canvas.addEventListener('mousemove', onMove);
    chart.canvas.addEventListener('mouseleave', onLeave);
  }
  attachHover(latencyChart); attachHover(errorChart); attachHover(memoryChart);

  // Inicialização: marca como carregando e busca
  markLoading(true);
  fetchAnalyze();
  setInterval(fetchAnalyze, 8000);
})();
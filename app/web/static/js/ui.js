// Global UI microinteractions and transitions
(function() {
  const root = document.documentElement;
  const body = document.body;

  // Apply page fade-in
  body.classList.add('page-fade-in');

  // Module slide-in on content container
  const content = document.querySelector('main.content');
  if (content) {
    content.classList.add('module-slide-in');
  }

  // Enhance buttons: amber loading and emerald success via classes
  const buttons = Array.from(document.querySelectorAll('button, .btn'));
  buttons.forEach(btn => {
    if (btn.dataset.uiWired === '1') return;
    btn.dataset.uiWired = '1';

    btn.addEventListener('click', () => {
      if (btn.matches('[data-action]')) {
        btn.classList.add('loading', 'amber');
      }
    });

    btn.addEventListener('action:success', () => {
      btn.classList.remove('loading');
      btn.classList.remove('amber');
      btn.classList.add('success');
      setTimeout(() => {
        btn.classList.remove('success');
      }, 1000);
    });

    btn.addEventListener('action:error', () => {
      btn.classList.remove('loading');
      btn.classList.remove('amber');
    });
  });

  // Hover glow for chart points is handled in charts.js; ensure canvas has pointer events enabled
  document.querySelectorAll('canvas.chart').forEach(cv => {
    cv.style.pointerEvents = 'auto';
  });
})();
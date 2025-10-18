document.addEventListener('DOMContentLoaded', () => {
  const links = document.querySelectorAll('.side-nav a.side-link');
  const normalize = (s) => {
    if (!s) return '/';
    const trimmed = s.replace(/\/+$/, '');
    return trimmed.length ? trimmed : '/';
  };
  const current = normalize(window.location.pathname);
  links.forEach(link => {
    const href = normalize(link.getAttribute('href'));
    if (href === current) link.classList.add('active');
  });
});
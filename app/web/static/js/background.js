document.addEventListener('DOMContentLoaded', () => {
  const grid = document.querySelector('.bg-grid');
  const circuit = document.querySelector('.bg-circuit');
  if (!grid || !circuit) return;

  let lastScrollY = window.scrollY;
  let gridX = 0, gridY = 0;
  let circuitShift = 0;

  function onScroll() {
    const currentY = window.scrollY;
    const deltaY = currentY - lastScrollY;
    lastScrollY = currentY;
    // parallax suave
    gridX += deltaY * 0.012;
    gridY += deltaY * 0.024;
    circuitShift += deltaY * 0.008;

    grid.style.transform = `translate3d(${gridX}px, ${gridY}px, 0)`;
    circuit.style.transform = `translate3d(${circuitShift}px, ${circuitShift}px, 0)`;
  }

  document.addEventListener('scroll', onScroll, { passive: true });

  // drift contínuo (visível mesmo sem rolagem)
  let driftX = 0, driftY = 0, driftC = 0;
  function autoDrift() {
    driftX += 0.02; // ~1.2px/s
    driftY += 0.015; // ~0.9px/s
    driftC += 0.012;
    grid.style.backgroundPosition = `${driftX}px ${driftY}px`;
    circuit.style.backgroundPosition = `${driftC}px ${driftC}px`;
    requestAnimationFrame(autoDrift);
  }
  autoDrift();

  // pulsos esporádicos de brilho em circuitos (sutil e não-distrativo)
  function pulseCircuit() {
    const intensity = 0.03 + Math.random() * 0.06; // 0.03–0.09
    circuit.style.opacity = intensity.toFixed(3);
    const duration = 3500 + Math.random() * 6500; // 3.5–10s
    setTimeout(pulseCircuit, duration);
  }
  pulseCircuit();
});
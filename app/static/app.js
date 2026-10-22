// Vanilla JS: small progressive enhancements. Every rule is also enforced server-side.
document.addEventListener("DOMContentLoaded", () => {
  // Simulation sliders: show the live percentage next to the control.
  document.querySelectorAll("input[type=range][data-out]").forEach(r => {
    const out = document.getElementById(r.dataset.out);
    const show = () => { out.textContent = r.value + "%"; };
    r.addEventListener("input", show); show();
  });
  // Ask before irreversible actions (applying a plan reserves stock).
  document.querySelectorAll("form[data-confirm]").forEach(f =>
    f.addEventListener("submit", e => { if (!confirm(f.dataset.confirm)) e.preventDefault(); }));
  // Prevent double submits on slow connections.
  document.querySelectorAll("form").forEach(f => f.addEventListener("submit", () => {
    const b = f.querySelector("button:not(.link)"); if (b) setTimeout(() => { b.disabled = true; }, 0);
  }));
  // Client-side range check for number fields (friendly message before the server check).
  document.querySelectorAll("input[type=number][min][max]").forEach(i =>
    i.addEventListener("invalid", () => i.setCustomValidity("Enter a number between " + i.min + " and " + i.max), false) ||
    i.addEventListener("input", () => i.setCustomValidity("")));
});

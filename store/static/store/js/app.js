document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.mobile-toggle');
  const nav = document.querySelector('.main-nav');
  if (toggle && nav) toggle.addEventListener('click', () => nav.classList.toggle('open'));

  document.querySelectorAll('[data-confirm]').forEach((button) => {
    button.addEventListener('click', (event) => {
      if (!window.confirm(button.dataset.confirm)) event.preventDefault();
    });
  });

  setTimeout(() => {
    document.querySelectorAll('.alert').forEach((alert) => {
      alert.style.transition = 'opacity .4s ease';
      alert.style.opacity = '0.8';
    });
  }, 3500);
});

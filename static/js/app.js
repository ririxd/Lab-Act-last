document.addEventListener('DOMContentLoaded', () => {
  const flashEls = document.querySelectorAll('.flash');
  flashEls.forEach((flash) => {
    setTimeout(() => {
      flash.style.opacity = '0';
      flash.style.transition = 'opacity 0.35s ease';
      setTimeout(() => flash.remove(), 350);
    }, 3500);
  });
});

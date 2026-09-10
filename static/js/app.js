const clearAuthForms = () => {
  document.querySelectorAll('form[data-clear-on-load]').forEach((form) => {
    form.reset();
    form.querySelectorAll('input').forEach((input) => {
      input.value = '';
    });
  });
};

document.addEventListener('DOMContentLoaded', () => {
  clearAuthForms();

  const flashEls = document.querySelectorAll('.flash');
  flashEls.forEach((flash) => {
    setTimeout(() => {
      flash.style.opacity = '0';
      flash.style.transition = 'opacity 0.35s ease';
      setTimeout(() => flash.remove(), 350);
    }, 3500);
  });
});

window.addEventListener('pageshow', clearAuthForms);

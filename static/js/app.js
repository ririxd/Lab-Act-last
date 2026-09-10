const clearAuthForms = () => {
  document.querySelectorAll('form[data-clear-on-load]').forEach((form) => {
    form.reset();
    form.querySelectorAll('input').forEach((input) => {
      input.value = '';
    });
  });
};

const setupPasswordToggles = () => {
  document.querySelectorAll('[data-password-toggle]').forEach((toggle) => {
    toggle.addEventListener('click', () => {
      const input = toggle.closest('.password-field').querySelector('input');
      const isVisible = input.type === 'text';
      input.type = isVisible ? 'password' : 'text';
      const label = isVisible ? 'Show password' : 'Hide password';
      toggle.classList.toggle('is-visible', !isVisible);
      toggle.setAttribute('aria-label', label);
      toggle.setAttribute('title', label);
    });
  });
};

document.addEventListener('DOMContentLoaded', () => {
  clearAuthForms();
  setupPasswordToggles();

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

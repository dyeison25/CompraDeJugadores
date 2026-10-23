document.querySelectorAll('[data-dismiss]').forEach(button => {
  button.addEventListener('click', () => button.closest('.flash').remove());
});
document.querySelectorAll('[data-toggle-password]').forEach(button => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.togglePassword);
    const showing = input.type === 'password';
    input.type = showing ? 'text' : 'password';
    button.setAttribute('aria-label', showing ? 'Ocultar contraseña' : 'Mostrar contraseña');
    button.setAttribute('aria-pressed', String(showing));
  });
});
document.querySelectorAll('img[data-fallback]').forEach(img => {
  const fallback = () => {
    if (!img.dataset.failed) {
      img.dataset.failed = '1';
      img.src = img.dataset.fallback;
    }
  };
  img.addEventListener('error', fallback);
  if (img.complete && img.naturalWidth === 0) fallback();
});
const photoInput = document.querySelector('[data-photo-input]');
let previewUrl;
if (photoInput) photoInput.addEventListener('change', () => {
  const file = photoInput.files[0];
  const label = document.querySelector('[data-file-name]');
  photoInput.setCustomValidity('');
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) {
    photoInput.setCustomValidity('La foto no puede superar los 5 MB.');
    photoInput.reportValidity();
    label.textContent = 'Selecciona una imagen de menos de 5 MB.';
    return;
  }
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    photoInput.setCustomValidity('Usa una imagen JPG, PNG o WebP.');
    photoInput.reportValidity();
    return;
  }
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  const preview = document.getElementById('photo-preview');
  delete preview.dataset.failed;
  preview.src = previewUrl;
  label.textContent = file.name;
});
document.querySelectorAll('form[method="post"]').forEach(form => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"],button:not([type])');
    if (button) { button.disabled = true; button.setAttribute('aria-busy', 'true'); }
  });
});

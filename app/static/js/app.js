document.querySelectorAll('.toggle-secret').forEach((button) => {
  button.addEventListener('click', () => {
    const input = button.parentElement.querySelector('.secret-field');
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    button.textContent = isPassword ? 'ocultar' : '****';
  });
});

const machineForm = document.getElementById('machine-form');
if (machineForm) {
  const selectedList = document.getElementById('selected-machines');
  const totalPrice = document.getElementById('total-price');
  const checkboxes = Array.from(machineForm.querySelectorAll('input[type="checkbox"][name="machine_ids"]'));

  function money(value) {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  function updateSelection() {
    let total = 0;
    const items = [];
    checkboxes.forEach((checkbox) => {
      const card = checkbox.closest('.machine-seat, .machine-card');
      if (checkbox.checked) {
        total += Number(card.dataset.price || 0);
        items.push(String(card.dataset.machineLabel || '').padStart(2, '0'));
        card.classList.add('is-selected');
      } else {
        card.classList.remove('is-selected');
      }
    });

    if (items.length) {
      selectedList.classList.remove('is-empty');
      selectedList.innerHTML = items
        .sort((a, b) => Number(a) - Number(b))
        .map((label) => `<span class="selected-badge">${label}</span>`)
        .join('');
    } else {
      selectedList.classList.add('is-empty');
      selectedList.textContent = 'Nenhuma máquina selecionada.';
    }

    totalPrice.textContent = money(total);
  }

  checkboxes.forEach((checkbox) => checkbox.addEventListener('change', updateSelection));
  updateSelection();
}

const mapModal = document.getElementById('map-modal');
if (mapModal) {
  const viewport = mapModal.querySelector('[data-map-viewport]');
  const mapImage = mapModal.querySelector('[data-map-image]');
  const zoomInButton = mapModal.querySelector('[data-zoom-in]');
  const zoomOutButton = mapModal.querySelector('[data-zoom-out]');
  const zoomResetButton = mapModal.querySelector('[data-zoom-reset]');
  let scale = 1;
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let startScrollLeft = 0;
  let startScrollTop = 0;

  function applyZoom(nextScale) {
    if (!mapImage) return;
    scale = Math.min(4, Math.max(1, nextScale));
    mapImage.style.transform = `scale(${scale})`;
    if (zoomResetButton) {
      zoomResetButton.textContent = `${Math.round(scale * 100)}%`;
    }
  }

  function openMap() {
    mapModal.hidden = false;
    document.body.classList.add('modal-open');
    applyZoom(1);
    if (viewport) {
      viewport.scrollTop = 0;
      viewport.scrollLeft = 0;
    }
  }

  function closeMap() {
    mapModal.hidden = true;
    document.body.classList.remove('modal-open');
  }

  document.querySelectorAll('[data-open-map]').forEach((button) => {
    button.addEventListener('click', openMap);
  });
  document.querySelectorAll('[data-close-map]').forEach((button) => {
    button.addEventListener('click', closeMap);
  });

  if (zoomInButton) zoomInButton.addEventListener('click', () => applyZoom(scale + 0.25));
  if (zoomOutButton) zoomOutButton.addEventListener('click', () => applyZoom(scale - 0.25));
  if (zoomResetButton) zoomResetButton.addEventListener('click', () => applyZoom(1));

  if (viewport) {
    viewport.addEventListener('wheel', (event) => {
      if (!mapModal.hidden && event.ctrlKey) {
        event.preventDefault();
        applyZoom(scale + (event.deltaY < 0 ? 0.2 : -0.2));
      }
    }, { passive: false });

    viewport.addEventListener('mousedown', (event) => {
      if (scale <= 1) return;
      isDragging = true;
      dragStartX = event.clientX;
      dragStartY = event.clientY;
      startScrollLeft = viewport.scrollLeft;
      startScrollTop = viewport.scrollTop;
      viewport.classList.add('is-dragging');
    });

    window.addEventListener('mousemove', (event) => {
      if (!isDragging) return;
      viewport.scrollLeft = startScrollLeft - (event.clientX - dragStartX);
      viewport.scrollTop = startScrollTop - (event.clientY - dragStartY);
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
      viewport.classList.remove('is-dragging');
    });
  }

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !mapModal.hidden) {
      closeMap();
    }
  });
}


function slugifyValue(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

document.querySelectorAll('[data-slug-source]').forEach((input) => {
  const targetSelector = input.getAttribute('data-slug-target');
  const target = targetSelector ? document.querySelector(targetSelector) : null;
  if (!target) return;

  const syncSlug = () => {
    if (target.dataset.userEdited === '1') return;
    target.value = slugifyValue(input.value);
  };

  input.addEventListener('input', syncSlug);
  target.addEventListener('input', () => {
    target.dataset.userEdited = target.value ? '1' : '0';
  });
  syncSlug();
});

document.querySelectorAll('[data-toggle-panel]').forEach((button) => {
  button.addEventListener('click', () => {
    const panelId = button.getAttribute('data-toggle-panel');
    const panel = panelId ? document.getElementById(panelId) : null;
    if (!panel) return;
    const isHidden = panel.hasAttribute('hidden');
    document.querySelectorAll('.admin-event-panel').forEach((item) => {
      if (item !== panel) item.setAttribute('hidden', 'hidden');
    });
    if (isHidden) {
      panel.removeAttribute('hidden');
      button.textContent = 'Fechar edição';
    } else {
      panel.setAttribute('hidden', 'hidden');
      button.textContent = 'Editar';
    }
  });
});

const adminModal = document.getElementById('default-event-modal');
if (adminModal) {
  document.querySelectorAll('[data-open-modal="default-event-modal"]').forEach((button) => {
    button.addEventListener('click', () => {
      adminModal.hidden = false;
      document.body.classList.add('modal-open');
    });
  });

  adminModal.querySelectorAll('[data-close-modal]').forEach((button) => {
    button.addEventListener('click', () => {
      adminModal.hidden = true;
      document.body.classList.remove('modal-open');
    });
  });
}

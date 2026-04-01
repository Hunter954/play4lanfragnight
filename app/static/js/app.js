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
  document.querySelectorAll('[data-open-map]').forEach((button) => {
    button.addEventListener('click', () => {
      mapModal.hidden = false;
      document.body.classList.add('modal-open');
    });
  });
  document.querySelectorAll('[data-close-map]').forEach((button) => {
    button.addEventListener('click', () => {
      mapModal.hidden = true;
      document.body.classList.remove('modal-open');
    });
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

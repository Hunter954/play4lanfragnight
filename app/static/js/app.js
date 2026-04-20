document.querySelectorAll('.toggle-secret').forEach((button) => {
  const setSecretButtonState = (isVisible) => {
    button.setAttribute('aria-pressed', isVisible ? 'true' : 'false');
    button.innerHTML = isVisible
      ? '<i class="bi bi-eye-slash"></i><span>Ocultar</span>'
      : '<i class="bi bi-eye"></i><span>Mostrar</span>';
  };

  setSecretButtonState(false);

  button.addEventListener('click', () => {
    const input = button.parentElement.querySelector('.secret-field');
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    setSecretButtonState(isPassword);
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
  function openMap() {
    mapModal.hidden = false;
    document.body.classList.add('modal-open');
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

    document.querySelectorAll('[data-toggle-panel]').forEach((otherButton) => {
      if (otherButton !== button) {
        otherButton.innerHTML = otherButton.dataset.openLabel || 'Editar';
      }
    });

    document.querySelectorAll('.admin-event-panel').forEach((item) => {
      if (item !== panel) item.setAttribute('hidden', 'hidden');
    });

    const openLabel = button.dataset.openLabel || 'Editar';
    const closeLabel = button.dataset.closeLabel || 'Fechar edição';

    if (isHidden) {
      panel.removeAttribute('hidden');
      button.innerHTML = closeLabel;
      panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
      panel.setAttribute('hidden', 'hidden');
      button.innerHTML = openLabel;
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

const groupCreateForm = document.querySelector('[data-group-create-form]');
if (groupCreateForm) {
  document.querySelectorAll('[data-group-preset]').forEach((button) => {
    button.addEventListener('click', () => {
      const preset = JSON.parse(button.getAttribute('data-group-preset') || '{}');
      const fields = {
        name: groupCreateForm.querySelector('[name="name"]'),
        layout: groupCreateForm.querySelector('[name="layout_key"]'),
        location: groupCreateForm.querySelector('[name="location_label"]'),
        quantity: groupCreateForm.querySelector('[name="quantity"]'),
        color: groupCreateForm.querySelector('[name="color"]'),
        specs: groupCreateForm.querySelector('[name="specs"]'),
      };

      if (fields.name) fields.name.value = preset.name || '';
      if (fields.layout) fields.layout.value = preset.layout || '';
      if (fields.location) fields.location.value = preset.location || '';
      if (fields.quantity) fields.quantity.value = preset.quantity || '';
      if (fields.color) fields.color.value = preset.color || '#0057e1';
      if (fields.specs) fields.specs.value = preset.specs || '';

      document.querySelectorAll('[data-group-preset]').forEach((item) => item.classList.remove('is-active'));
      button.classList.add('is-active');
    });
  });
}

const userMenu = document.querySelector('[data-user-menu]');
if (userMenu) {
  const trigger = userMenu.querySelector('[data-user-menu-trigger]');
  const panel = userMenu.querySelector('[data-user-menu-panel]');

  const closeUserMenu = () => {
    userMenu.classList.remove('is-open');
    trigger?.setAttribute('aria-expanded', 'false');
    panel?.setAttribute('hidden', 'hidden');
  };

  const openUserMenu = () => {
    userMenu.classList.add('is-open');
    trigger?.setAttribute('aria-expanded', 'true');
    panel?.removeAttribute('hidden');
  };

  trigger?.addEventListener('click', (event) => {
    event.stopPropagation();
    if (userMenu.classList.contains('is-open')) {
      closeUserMenu();
    } else {
      openUserMenu();
    }
  });

  document.addEventListener('click', (event) => {
    if (!userMenu.contains(event.target)) closeUserMenu();
  });

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeUserMenu();
  });
}

const machineActionModal = document.getElementById('machine-action-modal');
if (machineActionModal) {
  const labelEl = machineActionModal.querySelector('#machine-modal-label');
  const groupEl = machineActionModal.querySelector('#machine-modal-group');
  const statusEl = machineActionModal.querySelector('#machine-modal-status');
  const priceEl = machineActionModal.querySelector('#machine-modal-price');
  const reservedByEl = machineActionModal.querySelector('#machine-modal-reserved-by');
  const paymentEl = machineActionModal.querySelector('#machine-modal-payment');
  const actionsEl = machineActionModal.querySelector('#machine-modal-actions');
  const reserveForm = machineActionModal.querySelector('#machine-reserve-form');
  const updateForm = machineActionModal.querySelector('#machine-update-form');
  const releaseForm = machineActionModal.querySelector('#machine-release-form');
  const releaseReservationId = machineActionModal.querySelector('#release-reservation-id');
  const updateReservationId = machineActionModal.querySelector('#update-reservation-id');
  const reserveMachineId = machineActionModal.querySelector('#reserve-machine-id');
  const payerNameField = machineActionModal.querySelector('#reserve-payer-name');
  const paymentMethodField = machineActionModal.querySelector('#reserve-payment-method');
  const updatePayerNameField = machineActionModal.querySelector('#update-payer-name');
  const updatePaymentMethodField = machineActionModal.querySelector('#update-payment-method');

  const closeMachineModal = () => {
    machineActionModal.hidden = true;
    document.body.classList.remove('modal-open');
  };

  const formatPaymentLabel = (value) => {
    const labels = {
      pix: 'Pix',
      cartao: 'Cartão',
      dinheiro: 'Dinheiro',
      manual: 'A pagar',
      a_pagar: 'A pagar',
      '': '-',
    };
    return labels[value] || value;
  };

  document.querySelectorAll('[data-machine-modal-open]').forEach((button) => {
    button.addEventListener('click', () => {
      const status = button.dataset.machineStatus || 'available';
      const machineId = button.dataset.machineId || '';
      const reservedBy = button.dataset.machineReservedBy || '';
      const reservationId = button.dataset.machineReservationId || '';
      const paymentValue = button.dataset.machinePayment || '';

      labelEl.textContent = button.dataset.machineLabel || '--';
      groupEl.textContent = button.dataset.machineGroup || 'Máquina';
      priceEl.textContent = button.dataset.machinePrice || 'R$ 0,00';
      reservedByEl.textContent = reservedBy || 'Sem reserva';
      paymentEl.textContent = formatPaymentLabel(paymentValue);
      reserveMachineId.value = machineId;
      const normalizedPayment = paymentValue === 'manual' ? 'a_pagar' : (paymentValue || 'pix');
      releaseReservationId.value = reservationId;
      updateReservationId.value = reservationId;
      payerNameField.value = reservedBy || '';
      paymentMethodField.value = normalizedPayment;
      updatePayerNameField.value = reservedBy || '';
      updatePaymentMethodField.value = normalizedPayment;

      let statusText = 'Disponível';
      let statusClass = 'badge';
      let toggleText = 'Desativar';

      if (status === 'disabled') {
        statusText = 'Desativada';
        statusClass = 'badge badge-danger';
        toggleText = 'Ativar';
      }
      if (status === 'reserved') {
        statusText = 'Reservada';
        statusClass = 'badge badge-live';
      }

      statusEl.className = statusClass;
      statusEl.textContent = statusText;

      actionsEl.innerHTML = '';
      if (status !== 'reserved') {
        actionsEl.innerHTML = `
          <form method="post">
            <input type="hidden" name="action" value="toggle_machine">
            <input type="hidden" name="machine_id" value="${machineId}">
            <button class="btn btn-ghost full" type="submit">${toggleText}</button>
          </form>
        `;
        reserveForm.removeAttribute('hidden');
        updateForm?.setAttribute('hidden', 'hidden');
        releaseForm?.setAttribute('hidden', 'hidden');
      } else {
        actionsEl.innerHTML = '';
        reserveForm.setAttribute('hidden', 'hidden');
        updateForm?.removeAttribute('hidden');
        releaseForm?.removeAttribute('hidden');
      }

      machineActionModal.hidden = false;
      document.body.classList.add('modal-open');
    });
  });

  machineActionModal.querySelectorAll('[data-close-modal]').forEach((button) => {
    button.addEventListener('click', closeMachineModal);
  });

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !machineActionModal.hidden) {
      closeMachineModal();
    }
  });
}

const homeCarousel = document.querySelector('[data-home-carousel]');
if (homeCarousel) {
  const cards = Array.from(homeCarousel.querySelectorAll('.hero-carousel-card'));
  const nextButton = homeCarousel.querySelector('[data-home-carousel-next]');
  let currentIndex = 0;
  let isAnimating = false;

  const renderCarousel = () => {
    cards.forEach((card, index) => {
      card.classList.remove('is-current', 'is-peek', 'is-offright', 'is-offleft');
      if (index === currentIndex) {
        card.classList.add('is-current');
      } else if (index === (currentIndex + 1) % cards.length) {
        card.classList.add('is-peek');
      } else if (index < currentIndex) {
        card.classList.add('is-offleft');
      } else {
        card.classList.add('is-offright');
      }
    });
  };

  nextButton?.addEventListener('click', () => {
    if (isAnimating) return;
    isAnimating = true;
    currentIndex = (currentIndex + 1) % cards.length;
    renderCarousel();
    window.setTimeout(() => {
      isAnimating = false;
    }, 520);
  });

  renderCarousel();
}


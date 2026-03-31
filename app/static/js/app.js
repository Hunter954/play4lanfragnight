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
        items.push(`Máquina ${card.dataset.machineLabel}`);
        card.classList.add('is-selected');
      } else {
        card.classList.remove('is-selected');
      }
    });
    selectedList.textContent = items.length ? items.join(', ') : 'Nenhuma máquina selecionada.';
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

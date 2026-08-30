document.querySelectorAll(".chip[data-amount]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.querySelector('input[name="amount"]');
    if (input) input.value = button.dataset.amount;
    document.querySelectorAll(".chip").forEach((el) => el.classList.remove("on"));
    button.classList.add("on");
  });
});

const amountInput = document.querySelector('input[name="amount"]');
if (amountInput) {
  const mark = () => {
    document.querySelectorAll(".chip[data-amount]").forEach((el) => {
      el.classList.toggle("on", el.dataset.amount === String(amountInput.value));
    });
  };
  amountInput.addEventListener("input", mark);
  mark();
}

const donors = document.getElementById("donors-box");
const toggle = document.getElementById("toggle-donors");
if (toggle && donors) {
  toggle.addEventListener("click", () => {
    donors.hidden = !donors.hidden;
  });
}

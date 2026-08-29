document.querySelectorAll(".chip[data-amount]").forEach((button) => {
  button.addEventListener("click", () => {
    const input = document.querySelector('input[name="amount"]');
    if (input) input.value = button.dataset.amount;
    document.querySelectorAll(".chip").forEach((el) => el.classList.remove("on"));
    button.classList.add("on");
  });
});
const donors = document.getElementById("donors-box");
const toggle = document.getElementById("toggle-donors");
if (toggle && donors) {
  toggle.addEventListener("click", () => {
    donors.hidden = !donors.hidden;
  });
}

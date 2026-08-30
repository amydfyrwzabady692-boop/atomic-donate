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

function syncPayMethod() {
  const card = document.querySelector('input[name="method"][value="card"]');
  const pane = document.getElementById("card-pay");
  const receipt = document.querySelector('input[name="receipt"]');
  const cta = document.getElementById("pay-cta");
  const on = Boolean(card && card.checked);
  if (pane) pane.hidden = !on;
  if (receipt) receipt.required = on;
  if (cta) cta.textContent = on ? "ارسال رسید" : "پرداخت امن";
  document.querySelectorAll(".pay-method").forEach((el) => {
    const input = el.querySelector("input");
    el.classList.toggle("on", Boolean(input && input.checked));
  });
}
document.querySelectorAll('input[name="method"]').forEach((el) => {
  el.addEventListener("change", syncPayMethod);
});
syncPayMethod();

const copyBtn = document.getElementById("copy-card");
if (copyBtn) {
  copyBtn.addEventListener("click", async () => {
    const value = copyBtn.dataset.card || "";
    try {
      await navigator.clipboard.writeText(value);
      copyBtn.textContent = "کپی شد";
      setTimeout(() => {
        copyBtn.textContent = "کپی شماره";
      }, 1400);
    } catch (_) {
      copyBtn.textContent = "کپی نشد";
    }
  });
}

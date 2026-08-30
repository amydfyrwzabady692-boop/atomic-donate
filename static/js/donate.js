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

const drop = document.getElementById("receipt-drop");
const receiptFile = document.getElementById("receipt-file");
const receiptName = document.getElementById("receipt-name");
const RECEIPT_MAX = 5 * 1024 * 1024;

function showReceipt(file) {
  if (!drop || !receiptFile) return;
  drop.classList.remove("bad", "has-file", "drag");
  if (receiptName) {
    receiptName.hidden = true;
    receiptName.textContent = "";
  }
  if (!file) return;
  if (file.size > RECEIPT_MAX) {
    drop.classList.add("bad");
    if (receiptName) {
      receiptName.hidden = false;
      receiptName.textContent = "حجم فایل بیشتر از ۵ مگابایت است";
    }
    receiptFile.value = "";
    return;
  }
  drop.classList.add("has-file");
  if (receiptName) {
    receiptName.hidden = false;
    receiptName.textContent = file.name;
  }
}

if (drop && receiptFile) {
  receiptFile.addEventListener("change", () => showReceipt(receiptFile.files[0]));
  ["dragenter", "dragover"].forEach((type) => {
    drop.addEventListener(type, (event) => {
      event.preventDefault();
      drop.classList.add("drag");
    });
  });
  ["dragleave", "drop"].forEach((type) => {
    drop.addEventListener(type, (event) => {
      event.preventDefault();
      drop.classList.remove("drag");
    });
  });
  drop.addEventListener("drop", (event) => {
    const file = event.dataTransfer && event.dataTransfer.files[0];
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    receiptFile.files = transfer.files;
    showReceipt(file);
  });
}

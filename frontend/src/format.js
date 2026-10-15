const moneyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export function formatMoney(value) {
  return moneyFormatter.format(Number(value));
}

export function formatStatus(status) {
  return status.replace("_", " ");
}

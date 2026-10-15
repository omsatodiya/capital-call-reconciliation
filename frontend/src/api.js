async function request(path, { org, method = "GET", body } = {}) {
  const headers = {};
  if (org) {
    headers["X-Organization"] = org;
  }

  const response = await fetch(`/api${path}`, { method, headers, body });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      data?.detail || `Request failed with status ${response.status}.`,
    );
  }
  return data;
}

export const api = {
  listOrganizations: () => request("/organizations/"),
  listTransactions: (org) => request("/transactions/", { org }),
  listLineItems: (org) => request("/line-items/", { org }),

  importStatement: (org, file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/imports/", { org, method: "POST", body: form });
  },

  approveMatch: (org, matchId) =>
    request(`/matches/${matchId}/approve/`, { org, method: "POST" }),
  rejectMatch: (org, matchId) =>
    request(`/matches/${matchId}/reject/`, { org, method: "POST" }),
  ignoreTransaction: (org, transactionId) =>
    request(`/transactions/${transactionId}/ignore/`, { org, method: "POST" }),
};

import { formatMoney, formatStatus } from "../format";

const OPEN_STATUSES = ["suggested", "needs_review"];

export default function TransactionTable({
  transactions,
  busyId,
  onApprove,
  onReject,
  onIgnore,
}) {
  if (transactions.length === 0) {
    return (
      <p className="empty">
        No transactions yet. Upload a bank statement to get started.
      </p>
    );
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Description</th>
          <th className="number">Amount</th>
          <th>Status</th>
          <th>Suggested match</th>
          <th>Reason</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {transactions.map((transaction) => {
          const visibleMatches = transaction.matches.filter(
            (match) => match.status !== "rejected",
          );
          const proposed = visibleMatches.filter(
            (match) => match.status === "proposed",
          );
          const busy = busyId === transaction.id;
          const canIgnore = OPEN_STATUSES.includes(transaction.status);

          return (
            <tr key={transaction.id}>
              <td>{transaction.date}</td>
              <td>{transaction.description}</td>
              <td className="number">{formatMoney(transaction.amount)}</td>
              <td>
                <span className={`badge ${transaction.status}`}>
                  {formatStatus(transaction.status)}
                </span>
              </td>
              <td>
                {visibleMatches.length === 0
                  ? "—"
                  : visibleMatches.map((match) => (
                      <div key={match.id}>
                        {match.investor_name}{" "}
                        <span className="muted">
                          ({match.expected_reference})
                        </span>
                      </div>
                    ))}
              </td>
              <td>
                {visibleMatches.map((match) => (
                  <div key={match.id}>{match.reason}</div>
                ))}
                {transaction.status === "needs_review" &&
                  transaction.review_reason && (
                    <div className="muted">{transaction.review_reason}</div>
                  )}
              </td>
              <td className="actions">
                {proposed.map((match) => (
                  <div key={match.id}>
                    <button
                      disabled={busy}
                      onClick={() => onApprove(transaction, match)}
                    >
                      Approve
                      {proposed.length > 1
                        ? ` ${match.expected_reference}`
                        : ""}
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => onReject(transaction, match)}
                    >
                      Reject
                    </button>
                  </div>
                ))}
                {canIgnore && (
                  <button disabled={busy} onClick={() => onIgnore(transaction)}>
                    Ignore
                  </button>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

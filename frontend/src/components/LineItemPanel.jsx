import { formatMoney, formatStatus } from "../format";

export default function LineItemPanel({ lineItems }) {
  if (lineItems.length === 0) {
    return (
      <p className="empty">No capital call line items for this organization.</p>
    );
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Reference</th>
          <th>Investor</th>
          <th>Call</th>
          <th className="number">Called</th>
          <th className="number">Funded</th>
          <th className="number">Remaining</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {lineItems.map((item) => (
          <tr key={item.id}>
            <td>{item.expected_reference}</td>
            <td>{item.investor_name}</td>
            <td>#{item.capital_call_number}</td>
            <td className="number">{formatMoney(item.amount_called)}</td>
            <td className="number">{formatMoney(item.amount_funded)}</td>
            <td className="number">{formatMoney(item.amount_remaining)}</td>
            <td>
              <span className={`badge ${item.status}`}>
                {formatStatus(item.status)}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

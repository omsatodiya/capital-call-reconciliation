import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import LineItemPanel from "./components/LineItemPanel";
import TransactionTable from "./components/TransactionTable";
import UploadForm from "./components/UploadForm";
import "./App.css";

const APP_NAME = "Your App Name";

export default function App() {
  const [organizations, setOrganizations] = useState([]);
  const [org, setOrg] = useState("");
  const [transactions, setTransactions] = useState([]);
  const [lineItems, setLineItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    api
      .listOrganizations()
      .then((list) => {
        setOrganizations(list);
        if (list.length > 0) {
          setOrg(list[0].slug);
        } else {
          setLoading(false);
        }
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const loadData = useCallback(async () => {
    if (!org) return;
    setLoading(true);
    try {
      const [transactionList, lineItemList] = await Promise.all([
        api.listTransactions(org),
        api.listLineItems(org),
      ]);
      setTransactions(transactionList);
      setLineItems(lineItemList);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [org]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function changeOrganization(slug) {
    setError("");
    setTransactions([]);
    setLineItems([]);
    setOrg(slug);
  }

  async function runAction(transactionId, action) {
    setBusyId(transactionId);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(err.message);
    } finally {
      await loadData();
      setBusyId(null);
    }
  }

  const approve = (transaction, match) =>
    runAction(transaction.id, () => api.approveMatch(org, match.id));
  const reject = (transaction, match) =>
    runAction(transaction.id, () => api.rejectMatch(org, match.id));
  const ignore = (transaction) =>
    runAction(transaction.id, () => api.ignoreTransaction(org, transaction.id));

  const firstLoad =
    loading && transactions.length === 0 && lineItems.length === 0;

  return (
    <div className="page">
      <header className="header">
        <h1>{APP_NAME}</h1>
        <label>
          Organization{" "}
          <select
            value={org}
            onChange={(event) => changeOrganization(event.target.value)}
          >
            {organizations.map((organization) => (
              <option key={organization.slug} value={organization.slug}>
                {organization.name}
              </option>
            ))}
          </select>
        </label>
      </header>

      {error && <div className="error">{error}</div>}

      {org && (
        <>
          <section>
            <h2>Import bank statement</h2>
            <UploadForm key={org} org={org} onImported={loadData} />
          </section>

          <section>
            <h2>
              Transactions{" "}
              {loading && !firstLoad && (
                <span className="muted">Refreshing…</span>
              )}
            </h2>
            {firstLoad ? (
              <p className="muted">Loading…</p>
            ) : (
              <TransactionTable
                transactions={transactions}
                busyId={busyId}
                onApprove={approve}
                onReject={reject}
                onIgnore={ignore}
              />
            )}
          </section>

          <section>
            <h2>Capital call line items</h2>
            {firstLoad ? (
              <p className="muted">Loading…</p>
            ) : (
              <LineItemPanel lineItems={lineItems} />
            )}
          </section>
        </>
      )}
    </div>
  );
}

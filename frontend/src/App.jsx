import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import LineItemPanel from "./components/LineItemPanel";
import UploadForm from "./components/UploadForm";
import "./App.css";

const APP_NAME = "Callwise";

export default function App() {
  const [organizations, setOrganizations] = useState([]);
  const [org, setOrg] = useState("");
  const [lineItems, setLineItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
      setLineItems(await api.listLineItems(org));
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
    setLineItems([]);
    setOrg(slug);
  }

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
      <section>
        <h2>Import bank statement</h2>
        <UploadForm key={org} org={org} onImported={loadData} />
      </section>
      <section>
        <h2>Capital call line items</h2>
        {loading && lineItems.length === 0 ? (
          <p className="muted">Loading…</p>
        ) : (
          <LineItemPanel lineItems={lineItems} />
        )}
      </section>
    </div>
  );
}

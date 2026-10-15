import { useState } from "react";
import { api } from "../api";

export default function UploadForm({ org, onImported }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file) return;

    setUploading(true);
    setError("");
    setSummary(null);
    try {
      setSummary(await api.importStatement(org, file));
      onImported();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <form onSubmit={handleSubmit} className="upload">
        <input
          className="file-input"
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => setFile(event.target.files[0] ?? null)}
        />
        <button
          className="btn btn-primary"
          type="submit"
          disabled={!file || uploading}
        >
          Upload
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {summary && (
        <div className="summary">
          <p>
            Imported <strong>{summary.imported}</strong> · Duplicates{" "}
            <strong>{summary.duplicates}</strong> · Errors{" "}
            <strong>{summary.errors.length}</strong>
          </p>
          {summary.errors.length > 0 && (
            <ul>
              {summary.errors.map((rowError) => (
                <li key={rowError.line}>
                  Line {rowError.line}: {rowError.message}
                </li>
              ))}
            </ul>
          )}
          {summary.duplicate_rows.length > 0 && (
            <ul className="muted">
              {summary.duplicate_rows.map((row) => (
                <li key={row.line}>
                  Line {row.line}: duplicate reference {row.reference}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

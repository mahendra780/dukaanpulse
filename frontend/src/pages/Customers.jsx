import { useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import { listCustomers, createCustomer } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, EmptyState, ErrorBanner } from "../components/Feedback";
import StatusBadge from "../components/StatusBadge";
import Modal from "../components/Modal";

function CreateCustomerModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    customer_name: "",
    phone: "",
    address: "",
    area: "",
    credit_limit: 0,
    payment_terms_days: 0,
    status: "ACTIVE",
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await createCustomer({
        ...form,
        credit_limit: Number(form.credit_limit),
        payment_terms_days: Number(form.payment_terms_days),
      });
      onCreated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Add customer" onClose={onClose}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Customer name</label>
            <input
              required
              minLength={2}
              value={form.customer_name}
              onChange={(e) =>
                setForm({ ...form, customer_name: e.target.value })
              }
            />
          </div>
          <div className="field">
            <label>Phone</label>
            <input
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
        </div>
        <div className="field">
          <label>Address</label>
          <input
            required
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
          />
        </div>
        <div className="field-row">
          <div className="field">
            <label>Area</label>
            <input
              required
              value={form.area}
              onChange={(e) => setForm({ ...form, area: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Credit limit</label>
            <input
              type="number"
              min="0"
              step="any"
              value={form.credit_limit}
              onChange={(e) =>
                setForm({ ...form, credit_limit: e.target.value })
              }
            />
          </div>
          <div className="field">
            <label>Payment terms (days)</label>
            <input
              type="number"
              min="0"
              value={form.payment_terms_days}
              onChange={(e) =>
                setForm({ ...form, payment_terms_days: e.target.value })
              }
            />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Create customer"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [area, setArea] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  const load = () => {
    setLoading(true);
    listCustomers({ search: search || undefined, area: area || undefined })
      .then(setCustomers)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [search, area]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Customers</h1>
          <p>
            {customers.length} customer{customers.length === 1 ? "" : "s"}
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> Add customer
        </button>
      </div>

      <div className="table-toolbar">
        <div style={{ position: "relative", maxWidth: 280, flex: 1 }}>
          <Search
            size={14}
            style={{
              position: "absolute",
              left: 10,
              top: 10,
              color: "var(--muted)",
            }}
          />
          <input
            style={{ paddingLeft: 30 }}
            placeholder="Search name or phone…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <input
          style={{ maxWidth: 200 }}
          placeholder="Filter by area"
          value={area}
          onChange={(e) => setArea(e.target.value)}
        />
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : customers.length === 0 ? (
        <EmptyState label="No customers found" />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>Area</th>
                <th className="num">Credit limit</th>
                <th className="num">Credit balance</th>
                <th className="num">Terms (days)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.customer_id}>
                  <td>{c.customer_name}</td>
                  <td>{c.phone || "—"}</td>
                  <td>{c.area}</td>
                  <td className="num">
                    ₹{c.credit_limit.toLocaleString("en-IN")}
                  </td>
                  <td className="num">
                    {c.credit_balance > 0 ? (
                      <span className="badge badge-accent">
                        ₹{c.credit_balance.toLocaleString("en-IN")}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="num">{c.payment_terms_days}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateCustomerModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}
    </div>
  );
}

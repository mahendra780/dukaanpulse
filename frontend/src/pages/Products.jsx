import { useEffect, useState } from "react";
import { Plus, Trash2, Search } from "lucide-react";
import { listProducts, listCategories, createProduct, updateProduct } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, EmptyState, ErrorBanner } from "../components/Feedback";
import StatusBadge from "../components/StatusBadge";
import Modal from "../components/Modal";
import { useToast } from "../components/ToastProvider";
import { useConfirm } from "../components/ConfirmProvider";
import { successMessage } from "../lib/messages";

const emptyPackaging = () => ({ unit_name: "", conversion_to_base: 1, is_base_unit: false, is_purchase_unit: false, is_sale_unit: false });

function CreateProductModal({ categories, onClose, onCreated }) {
  const [form, setForm] = useState({ product_name: "", brand_name: "", sku: "", category_id: categories[0]?.category_id ?? "", status: "ACTIVE" });
  const [packaging, setPackaging] = useState([{ ...emptyPackaging(), unit_name: "PIECE", is_base_unit: true, is_sale_unit: true }]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const updatePkg = (i, field, value) => {
    setPackaging((rows) => rows.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)));
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await createProduct({
        ...form,
        category_id: Number(form.category_id),
        packaging: packaging.map((p) => ({ ...p, conversion_to_base: Number(p.conversion_to_base) })),
      });
      toast.success(successMessage("Product", "added"));
      onCreated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Add product" onClose={onClose} maxWidth={680}>
      <form onSubmit={submit}>
        <ErrorBanner message={error} />
        <div className="field-row">
          <div className="field">
            <label>Product name</label>
            <input required value={form.product_name} onChange={(e) => setForm({ ...form, product_name: e.target.value })} />
          </div>
          <div className="field">
            <label>Brand</label>
            <input value={form.brand_name} onChange={(e) => setForm({ ...form, brand_name: e.target.value })} />
          </div>
        </div>
        <div className="field-row">
          <div className="field">
            <label>SKU</label>
            <input required value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} />
          </div>
          <div className="field">
            <label>Category</label>
            <select required value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
              {categories.map((c) => (
                <option key={c.category_id} value={c.category_id}>{c.category_name}</option>
              ))}
            </select>
          </div>
        </div>

        <label style={{ marginTop: 6 }}>Packaging units</label>
        {packaging.map((p, i) => (
          <div className="item-row" key={i} style={{ gridTemplateColumns: "1.3fr 1fr auto auto auto auto" }}>
            <input placeholder="Unit name (e.g. CARTON)" required value={p.unit_name} onChange={(e) => updatePkg(i, "unit_name", e.target.value)} />
            <input type="number" min="0.0001" step="any" placeholder="Conv. to base" required value={p.conversion_to_base} onChange={(e) => updatePkg(i, "conversion_to_base", e.target.value)} />
            <label style={{ display: "flex", alignItems: "center", gap: 4, fontWeight: 400 }}>
              <input type="checkbox" style={{ width: "auto" }} checked={p.is_base_unit} onChange={(e) => updatePkg(i, "is_base_unit", e.target.checked)} /> Base
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 4, fontWeight: 400 }}>
              <input type="checkbox" style={{ width: "auto" }} checked={p.is_purchase_unit} onChange={(e) => updatePkg(i, "is_purchase_unit", e.target.checked)} /> Purchase
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 4, fontWeight: 400 }}>
              <input type="checkbox" style={{ width: "auto" }} checked={p.is_sale_unit} onChange={(e) => updatePkg(i, "is_sale_unit", e.target.checked)} /> Sale
            </label>
            <button type="button" className="btn btn-ghost" onClick={() => setPackaging((rows) => rows.filter((_, idx) => idx !== i))} disabled={packaging.length === 1}>
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        <button type="button" className="btn btn-secondary" style={{ marginTop: 4 }} onClick={() => setPackaging((rows) => [...rows, emptyPackaging()])}>
          <Plus size={14} /> Add unit
        </button>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? "Saving…" : "Create product"}</button>
        </div>
      </form>
    </Modal>
  );
}

export default function Products() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const toast = useToast();
  const confirm = useConfirm();

  const load = () => {
    setLoading(true);
    Promise.all([listProducts(search || undefined), listCategories()])
      .then(([p, c]) => {
        setProducts(p);
        setCategories(c);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
    
  }, [search]);

  const toggleStatus = async (product) => {
    const activating = product.status !== "ACTIVE";

    if (!activating) {
      const ok = await confirm({
        title: "Deactivate this product?",
                       description: `"${product.product_name}" will no longer be offered when creating new purchases or orders. Existing records are not affected, and you can reactivate it anytime.`,
        confirmLabel: "Deactivate",
        danger: true,
      });
      if (!ok) return;
    }

    setBusyId(product.product_id);
    try {
      await updateProduct(product.product_id, { status: activating ? "ACTIVE" : "INACTIVE" });
      toast.success(successMessage("Product", activating ? "activated" : "deactivated"));
      load();
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Products</h1>
          <p>{products.length} product{products.length === 1 ? "" : "s"}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)} disabled={categories.length === 0}>
          <Plus size={15} /> Add product
        </button>
      </div>

      <div className="table-toolbar">
        <div style={{ position: "relative", maxWidth: 320, flex: 1 }}>
          <Search size={14} style={{ position: "absolute", left: 10, top: 10, color: "var(--muted)" }} />
          <input style={{ paddingLeft: 30 }} placeholder="Search name, brand or SKU…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>

      <ErrorBanner message={error} />

      {loading ? (
        <Spinner />
      ) : products.length === 0 ? (
        <EmptyState
          label={
            search
              ? "No products match your search."
              : "No products found. Add your first product to start managing your inventory."
          }
        />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th>Category</th>
                <th className="num">Stock</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.product_id}>
                  <td>{p.product_name}{p.brand_name ? <span className="muted"> · {p.brand_name}</span> : null}</td>
                  <td>{p.sku}</td>
                  <td>{p.category || "—"}</td>
                  <td className="num">{p.current_stock} {p.base_unit}</td>
                  <td><StatusBadge status={p.status} /></td>
                  <td>
                    <button className="btn btn-ghost" disabled={busyId === p.product_id} onClick={() => toggleStatus(p)}>
                      {busyId === p.product_id
                        ? (p.status === "ACTIVE" ? "Deactivating…" : "Activating…")
                        : (p.status === "ACTIVE" ? "Deactivate" : "Activate")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateProductModal
          categories={categories}
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
import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { listProducts, getProductStock } from "../api/endpoints";
import { extractErrorMessage } from "../api/client";
import { Spinner, ErrorBanner, EmptyState } from "../components/Feedback";
import StatCard from "../components/StatCard";

export default function Inventory() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [productId, setProductId] = useState("");
  const [stock, setStock] = useState(null);
  const [loadingProducts, setLoadingProducts] = useState(true);
  const [loadingStock, setLoadingStock] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      setLoadingProducts(true);
      listProducts(search || undefined)
        .then(setProducts)
        .catch((err) => setError(extractErrorMessage(err)))
        .finally(() => setLoadingProducts(false));
    }, 250);
    return () => clearTimeout(t);
  }, [search]);

  const lookup = (id) => {
    if (!id) return;
    setProductId(id);
    setLoadingStock(true);
    setError("");
    getProductStock(id)
      .then(setStock)
      .catch((err) => {
        setError(extractErrorMessage(err));
        setStock(null);
      })
      .finally(() => setLoadingStock(false));
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Stock lookup</h1>
          <p>Current stock for a single product</p>
        </div>
      </div>

      <div className="table-toolbar">
        <div style={{ position: "relative", maxWidth: 320, flex: 1 }}>
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
            placeholder="Search product…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          style={{ maxWidth: 280 }}
          value={productId}
          onChange={(e) => lookup(e.target.value)}
          disabled={loadingProducts || products.length === 0}
        >
          <option value="" disabled>
            {loadingProducts ? "Loading…" : "Select a product…"}
          </option>
          {products.map((p) => (
            <option key={p.product_id} value={p.product_id}>
              {p.product_name}
              {p.brand_name ? ` · ${p.brand_name}` : ""}
            </option>
          ))}
        </select>
      </div>

      <ErrorBanner message={error} />

      {loadingStock ? (
        <Spinner label="Checking stock…" />
      ) : stock ? (
        <div className="panel">
          <h3 className="panel-title">{stock.product_name}</h3>
          <div className="stat-grid">
            <StatCard
              label="Current stock"
              value={`${stock.current_stock} ${stock.base_unit || ""}`}
            />
          </div>
          {!stock.base_unit && (
            <p className="muted">
              No base packaging unit is defined for this product.
            </p>
          )}
        </div>
      ) : (
        <EmptyState label="Search and select a product to see its current stock" />
      )}
    </div>
  );
}

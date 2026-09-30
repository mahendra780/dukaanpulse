export default function ProductPackagingSelect({ products, productId, packagingId, onChange, filterPackaging }) {
  const product = products.find((p) => p.product_id === Number(productId));
  const packagingOptions = product
    ? product.packaging.filter((pk) => (filterPackaging ? filterPackaging(pk) : true))
    : [];

  return (
    <>
      <select
        required
        value={productId || ""}
        onChange={(e) => {
          const newProduct = products.find((p) => p.product_id === Number(e.target.value));
          const options = newProduct ? newProduct.packaging.filter((pk) => (filterPackaging ? filterPackaging(pk) : true)) : [];
          const defaultPkg = options[0]?.packaging_id || "";
          onChange(e.target.value, defaultPkg);
        }}
      >
        <option value="" disabled>Select product…</option>
        {products.map((p) => (
          <option key={p.product_id} value={p.product_id}>{p.product_name}</option>
        ))}
      </select>
      <select
        required
        value={packagingId || ""}
        onChange={(e) => onChange(productId, e.target.value)}
        disabled={!product}
      >
        <option value="" disabled>Unit…</option>
        {packagingOptions.map((pk) => (
          <option key={pk.packaging_id} value={pk.packaging_id}>{pk.unit_name}</option>
        ))}
      </select>
    </>
  );
}

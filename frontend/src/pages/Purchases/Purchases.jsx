import { useEffect, useMemo, useState } from "react";
import { useFieldArray, useForm, Controller } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-toastify";
import {
  CalendarDays,
  Clock,
  Eye,
  IndianRupee,
  MoreHorizontal,
  PackageCheck,
  Pencil,
  Plus,
  Save,
  Search,
  ShoppingCart,
  Trash2,
} from "lucide-react";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import AppSelect from "../../components/ui/AppSelect";
import Drawer from "../../components/ui/Drawer";
import api from "../../services/api";

const money = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 2,
});
const purchaseStatuses = [
  { value: "PENDING", label: "Pending" },
  { value: "RECEIVED", label: "Received" },
  { value: "CANCELLED", label: "Cancelled" },
];
const blankItem = {
  product_id: "",
  packaging_id: "",
  quantity: 1,
  received_quantity: 0,
  unit_price: 0,
  discount: 0,
  tax: 0,
};
const today = new Date().toLocaleDateString("en-CA");
const inputClass =
  "h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10";

const number = (value) => Number(value) || 0;
const currency = (value) => money.format(number(value));
const dateText = (value) =>
  value
    ? new Intl.DateTimeFormat("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }).format(new Date(`${value}T00:00:00`))
    : "--";
const lineTotal = (item) =>
  Math.max(
    0,
    number(item.quantity) * number(item.unit_price) -
      number(item.discount) +
      number(item.tax),
  );

function Skeleton({ className = "" }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-xl bg-emerald-300/10 ${className}`}
    />
  );
}

function StatusBadge({ status }) {
  const styles = {
    RECEIVED: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
    PENDING: "border-amber-400/25 bg-amber-400/10 text-amber-300",
    CANCELLED: "border-red-400/25 bg-red-400/10 text-red-300",
  };
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${styles[status] || "border-slate-400/20 bg-slate-400/10 text-slate-300"}`}
    >
      {status?.charAt(0) + status?.slice(1).toLowerCase() || "Unknown"}
    </span>
  );
}

function SummarySkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: 4 }, (_, index) => (
        <Skeleton
          key={index}
          className="h-[92px] rounded-3xl bg-white/[0.04]"
        />
      ))}
    </div>
  );
}

function PurchaseTableSkeleton() {
  return (
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/35">
      <div className="grid min-w-[1120px] grid-cols-[.7fr_1.5fr_1.1fr_1fr_1fr_.9fr_.7fr_.4fr] gap-4 border-b border-white/10 bg-white/[0.05] px-5 py-4">
        {Array.from({ length: 8 }, (_, index) => (
          <Skeleton key={index} className="h-3 w-16 bg-slate-400/10" />
        ))}
      </div>
      {Array.from({ length: 6 }, (_, row) => (
        <div
          key={row}
          className="grid min-w-[1120px] grid-cols-[.7fr_1.5fr_1.1fr_1fr_1fr_.9fr_.7fr_.4fr] items-center gap-4 border-b border-white/10 px-5 py-4 last:border-b-0"
        >
          {Array.from({ length: 8 }, (_, index) => (
            <Skeleton key={index} className="h-4 w-20 bg-slate-400/10" />
          ))}
        </div>
      ))}
    </div>
  );
}

function PurchaseActions({
  purchase,
  openMenuId,
  onToggle,
  onView,
  onEdit,
  onReceive,
}) {
  const open = openMenuId === purchase.purchase_id;
  return (
    <div className="relative flex justify-end">
      <button
        type="button"
        onClick={() => onToggle(open ? null : purchase.purchase_id)}
        className="grid h-9 w-9 place-items-center rounded-xl border border-transparent text-slate-400 transition hover:border-emerald-300/25 hover:bg-emerald-400/10 hover:text-emerald-200"
        aria-label={`Actions for purchase ${purchase.purchase_id}`}
        aria-expanded={open}
      >
        <MoreHorizontal size={18} />
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-30 w-44 rounded-2xl border border-white/15 bg-slate-900/95 p-1.5 shadow-2xl shadow-emerald-950/30 backdrop-blur-xl">
          <button
            type="button"
            onClick={() => onView(purchase)}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-emerald-400/10 hover:text-emerald-100"
          >
            <Eye size={15} />
            View Purchase
          </button>
          {purchase.status !== "RECEIVED" && (
            <button
              type="button"
              onClick={() => onEdit(purchase)}
              className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-emerald-400/10 hover:text-emerald-100"
            >
              <Pencil size={15} />
              Edit Purchase
            </button>
          )}
          {purchase.status === "PENDING" && (
            <button
              type="button"
              onClick={() => onReceive(purchase)}
              className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-emerald-300 transition hover:bg-emerald-400/10"
            >
              <PackageCheck size={15} />
              Mark as Received
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function DrawerTableSkeleton() {
  return (
    <div className="space-y-2 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
      {Array.from({ length: 3 }, (_, index) => (
        <Skeleton key={index} className="h-11 w-full bg-white/[0.04]" />
      ))}
    </div>
  );
}

function PurchaseDetails({ purchase }) {
  if (!purchase) return <DrawerTableSkeleton />;
  const info = [
    { label: "Purchase ID", value: `#${purchase.purchase_id}` },
    { label: "Supplier", value: purchase.supplier_name || "--" },
    { label: "Invoice Number", value: purchase.supplier_invoice_no || "--" },
    { label: "Purchase Date", value: dateText(purchase.purchase_date) },
  ];
  const amounts = [
    { label: "Subtotal", value: currency(purchase.subtotal) },
    { label: "Discount", value: currency(purchase.discount) },
    { label: "Tax", value: currency(purchase.tax) },
    { label: "Total Amount", value: currency(purchase.total_amount) },
  ];
  return (
    <div className="space-y-5">
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Purchase Information
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {info.map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-3.5"
            >
              <p className="text-[11px] uppercase tracking-wider text-slate-500">
                {item.label}
              </p>
              <p className="mt-1 break-words text-sm font-semibold text-slate-100">
                {item.value}
              </p>
            </div>
          ))}
          <div className="col-span-2 rounded-2xl border border-white/10 bg-white/[0.03] p-3.5">
            <p className="text-[11px] uppercase tracking-wider text-slate-500">
              Status
            </p>
            <div className="mt-2">
              <StatusBadge status={purchase.status} />
            </div>
          </div>
        </div>
      </section>
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Amount Summary
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {amounts.map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-3.5"
            >
              <p className="text-[11px] uppercase tracking-wider text-slate-500">
                {item.label}
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-100">
                {item.value}
              </p>
            </div>
          ))}
        </div>
      </section>
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Purchased Items
        </h3>
        <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.03]">
          <table className="min-w-[680px] w-full text-left text-xs">
            <thead className="bg-white/[0.05] uppercase tracking-wider text-slate-500">
              <tr>
                {[
                  "Product",
                  "Packaging",
                  "Quantity",
                  "Received",
                  "Unit Price",
                  "Line Total",
                ].map((heading) => (
                  <th key={heading} className="px-3 py-3 font-semibold">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {purchase.items?.map((item) => (
                <tr
                  key={
                    item.purchase_item_id ||
                    `${item.product_id}-${item.packaging_id}`
                  }
                  className="border-t border-white/10"
                >
                  <td className="px-3 py-3 font-semibold text-slate-100">
                    {item.product_name || "--"}
                  </td>
                  <td className="px-3 py-3">
                    <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 font-medium text-emerald-200">
                      {item.unit_name || "--"}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-slate-300">{item.quantity}</td>
                  <td className="px-3 py-3 text-slate-300">
                    {item.received_quantity}
                  </td>
                  <td className="px-3 py-3 text-slate-300">
                    {currency(item.unit_price)}
                  </td>
                  <td className="px-3 py-3 font-semibold text-slate-100">
                    {currency(item.line_total)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function PurchaseForm({
  suppliers,
  products,
  purchase,
  onSave,
  onClose,
  saving,
}) {
  const defaults = purchase
    ? {
        supplier_id: String(purchase.supplier_id),
        purchase_date: purchase.purchase_date || today,
        supplier_invoice_no: purchase.supplier_invoice_no || "",
        status: purchase.status || "PENDING",
        items: purchase.items?.map((item) => ({
          product_id: String(item.product_id),
          packaging_id: String(item.packaging_id),
          quantity: item.quantity,
          received_quantity: item.received_quantity,
          unit_price: item.unit_price,
          discount: item.discount,
          tax: item.tax,
        })) || [blankItem],
      }
    : {
        supplier_id: "",
        purchase_date: today,
        supplier_invoice_no: "",
        status: "PENDING",
        items: [blankItem],
      };
  const { control, register, handleSubmit, watch, reset, setValue } = useForm({
    defaultValues: defaults,
  });
  const { fields, append, remove } = useFieldArray({ control, name: "items" });
  const items = watch("items") || [];
  const totals = useMemo(
    () =>
      items.reduce(
        (result, item) => {
          const gross = number(item.quantity) * number(item.unit_price);
          result.subtotal += gross;
          result.discount += number(item.discount);
          result.tax += number(item.tax);
          result.total += lineTotal(item);
          return result;
        },
        { subtotal: 0, discount: 0, tax: 0, total: 0 },
      ),
    [items],
  );
  useEffect(() => {
    reset(defaults);
  }, [purchase, reset]);
  const productOptions = products
    .filter((product) => product.status !== "INACTIVE")
    .map((product) => ({
      value: String(product.product_id),
      label: product.product_name,
    }));
  const supplierOptions = suppliers
    .filter((supplier) => supplier.status !== "INACTIVE")
    .map((supplier) => ({
      value: String(supplier.supplier_id),
      label: supplier.supplier_name,
    }));
  const submit = (values) =>
    onSave({
      supplier_id: Number(values.supplier_id),
      purchase_date: values.purchase_date,
      supplier_invoice_no: values.supplier_invoice_no.trim(),
      status: values.status,
      subtotal: totals.subtotal,
      discount: totals.discount,
      tax: totals.tax,
      total_amount: totals.total,
      items: values.items.map((item) => ({
        product_id: Number(item.product_id),
        packaging_id: Number(item.packaging_id),
        quantity: number(item.quantity),
        received_quantity: number(item.received_quantity),
        unit_price: number(item.unit_price),
        discount: number(item.discount),
        tax: number(item.tax),
        line_total: lineTotal(item),
      })),
    });
  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-5">
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Purchase Details
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Supplier
            </span>
            <Controller
              control={control}
              name="supplier_id"
              rules={{ required: true }}
              render={({ field }) => (
                <AppSelect
                  value={field.value}
                  onValueChange={field.onChange}
                  options={supplierOptions}
                  placeholder="Select supplier"
                  ariaLabel="Supplier"
                />
              )}
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Purchase Date
            </span>
            <input
              type="date"
              required
              {...register("purchase_date")}
              className={inputClass}
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Supplier Invoice Number
            </span>
            <input
              required
              {...register("supplier_invoice_no")}
              className={inputClass}
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Status
            </span>
            <Controller
              control={control}
              name="status"
              render={({ field }) => (
                <AppSelect
                  value={field.value}
                  onValueChange={field.onChange}
                  options={purchaseStatuses}
                  ariaLabel="Purchase status"
                />
              )}
            />
          </label>
        </div>
      </section>
      <section className="border-t border-white/10 pt-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="font-semibold text-white">Purchase Items</h3>
          <button
            type="button"
            onClick={() => append(blankItem)}
            className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-300/25 bg-emerald-400/10 px-3 py-2 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-400/20"
          >
            <Plus size={15} />
            Add Item
          </button>
        </div>
        <div className="space-y-3">
          {fields.map((field, index) => {
            const productId = items[index]?.product_id;
            const product = products.find(
              (item) => String(item.product_id) === String(productId),
            );
            const packagingOptions = (product?.packaging || []).map(
              (packaging) => ({
                value: String(packaging.packaging_id),
                label: packaging.unit_name,
              }),
            );
            return (
              <div
                key={field.id}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-3.5"
              >
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-xs font-semibold text-slate-300">
                    Item {index + 1}
                  </p>
                  <button
                    type="button"
                    onClick={() => remove(index)}
                    disabled={fields.length === 1}
                    className="grid h-8 w-8 place-items-center rounded-lg text-slate-500 transition hover:bg-red-400/10 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-30"
                    aria-label="Remove purchase item"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label>
                    <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-slate-500">
                      Product
                    </span>
                    <Controller
                      control={control}
                      name={`items.${index}.product_id`}
                      rules={{ required: true }}
                      render={({ field: productField }) => (
                        <AppSelect
                          value={productField.value}
                          onValueChange={(value) => {
                            productField.onChange(value);
                            setValue(`items.${index}.packaging_id`, "");
                          }}
                          options={productOptions}
                          placeholder="Select product"
                          ariaLabel="Product"
                        />
                      )}
                    />
                  </label>
                  <label>
                    <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-slate-500">
                      Packaging
                    </span>
                    <Controller
                      control={control}
                      name={`items.${index}.packaging_id`}
                      rules={{ required: true }}
                      render={({ field: packagingField }) => (
                        <AppSelect
                          value={packagingField.value}
                          onValueChange={packagingField.onChange}
                          options={packagingOptions}
                          placeholder="Select packaging"
                          disabled={!product}
                          ariaLabel="Packaging"
                        />
                      )}
                    />
                  </label>
                  {[
                    { name: "quantity", label: "Quantity", min: "0.001" },
                    {
                      name: "received_quantity",
                      label: "Received Quantity",
                      min: "0",
                    },
                    { name: "unit_price", label: "Unit Price", min: "0" },
                    { name: "discount", label: "Discount", min: "0" },
                    { name: "tax", label: "Tax", min: "0" },
                  ].map(({ name, label, min }) => (
                    <label key={name}>
                      <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-slate-500">
                        {label}
                      </span>
                      <input
                        type="number"
                        step="any"
                        min={min}
                        max={
                          name === "received_quantity"
                            ? items[index]?.quantity
                            : undefined
                        }
                        required={name === "quantity" || name === "unit_price"}
                        {...register(`items.${index}.${name}`, {
                          valueAsNumber: true,
                        })}
                        className={inputClass}
                      />
                    </label>
                  ))}
                  <div className="rounded-xl border border-emerald-400/15 bg-emerald-400/[0.05] px-3 py-2.5">
                    <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
                      Line Total
                    </p>
                    <p className="mt-1 text-sm font-semibold text-emerald-200">
                      {currency(lineTotal(items[index]))}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>
      <section className="rounded-3xl border border-emerald-300/15 bg-emerald-400/[0.05] p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Amount Summary
        </h3>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Subtotal", value: totals.subtotal },
            { label: "Discount", value: totals.discount },
            { label: "Tax", value: totals.tax },
            { label: "Grand Total", value: totals.total },
          ].map((item) => (
            <div key={item.label}>
              <p className="text-[11px] uppercase tracking-wider text-slate-500">
                {item.label}
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-100">
                {currency(item.value)}
              </p>
            </div>
          ))}
        </div>
      </section>
      <div className="flex justify-end gap-3 border-t border-white/10 pt-5">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          <Save size={17} />
          {saving ? "Saving..." : purchase ? "Save Changes" : "Save Purchase"}
        </Button>
      </div>
    </form>
  );
}

function Purchases() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [supplierFilter, setSupplierFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [drawer, setDrawer] = useState(null);
  const [selectedPurchase, setSelectedPurchase] = useState(null);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [mobileActionPurchase, setMobileActionPurchase] = useState(null);
  const purchasesQuery = useQuery({
    queryKey: ["purchases"],
    queryFn: async () => (await api.get("/purchases")).data,
  });
  const suppliersQuery = useQuery({
    queryKey: ["suppliers"],
    queryFn: async () => (await api.get("/suppliers")).data,
    enabled: drawer === "add" || drawer === "edit",
  });
  const productsQuery = useQuery({
    queryKey: ["products"],
    queryFn: async () => (await api.get("/products")).data,
    enabled: drawer === "add" || drawer === "edit",
  });
  const createPurchase = useMutation({
    mutationFn: async (payload) => (await api.post("/purchases", payload)).data,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["purchases"] });
      toast.success(result.message || "Purchase created successfully");
      setDrawer(null);
    },
    onError: (error) =>
      toast.error(
        error?.response?.data?.detail ||
          "Unable to create purchase. Please try again.",
      ),
  });
  const updatePurchase = useMutation({
  mutationFn: async ({ purchaseId, payload }) => {
    const response = await api.patch(
      `/purchases/${purchaseId}`,
      payload
    );
    return response.data;
  },

  onSuccess: async (result) => {
    await queryClient.invalidateQueries({ queryKey: ["purchases"] });
    await queryClient.invalidateQueries({ queryKey: ["products"] });
    await queryClient.invalidateQueries({ queryKey: ["dashboard"] });

    toast.success(result.message || "Purchase updated successfully");

    setDrawer(null);
    setSelectedPurchase(null);
  },

  onError: (error) => {
    toast.error(
      error?.response?.data?.detail ||
      "Unable to update purchase."
    );
  },
});
  const updatePurchaseStatusMutation = useMutation({
  mutationFn: async ({ purchaseId, status }) => {
    const response = await api.patch(
      `/purchases/${purchaseId}/status`,
      { status }
    )
    return response.data
  },

  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['purchases'] })
    queryClient.invalidateQueries({ queryKey: ["products"] })
    queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    toast.success("Purchase status updated successfully")
  },

  onError: (error) => {
    toast.error(
      error?.response?.data?.detail ||
      "Unable to update purchase status"
    )
  }
  })
  const handleStatusChange = (purchaseId, status) => {
  updatePurchaseStatusMutation.mutate({
    purchaseId,
    status,
  });
};
  const purchases = Array.isArray(purchasesQuery.data)
    ? purchasesQuery.data
    : [];
  const supplierOptions = useMemo(
    () =>
      [
        ...new Map(
          purchases
            .filter((purchase) => purchase.supplier_id)
            .map((purchase) => [
              purchase.supplier_id,
              purchase.supplier_name || `Supplier #${purchase.supplier_id}`,
            ]),
        ).entries(),
      ].map(([value, label]) => ({ value: String(value), label })),
    [purchases],
  );
  const filteredPurchases = useMemo(() => {
    const term = search.trim().toLowerCase();
    return purchases.filter((purchase) => {
      const matchesSearch =
        !term ||
        [purchase.supplier_name, purchase.supplier_invoice_no].some((value) =>
          value?.toLowerCase().includes(term),
        );
      const date = purchase.purchase_date || "";
      return (
        matchesSearch &&
        (supplierFilter === "ALL" ||
          String(purchase.supplier_id) === supplierFilter) &&
        (statusFilter === "ALL" || purchase.status === statusFilter) &&
        (!fromDate || date >= fromDate) &&
        (!toDate || date <= toDate)
      );
    });
  }, [purchases, search, supplierFilter, statusFilter, fromDate, toDate]);
  const summary = useMemo(
    () => [
      {
        label: "Total Purchases",
        value: purchases.length,
        icon: ShoppingCart,
        iconClass: "from-sky-200 to-sky-600 text-sky-950",
      },
      {
        label: "Total Purchase Amount",
        value: currency(
          purchases.reduce(
            (total, purchase) => total + number(purchase.total_amount),
            0,
          ),
        ),
        icon: IndianRupee,
        iconClass: "from-emerald-200 to-emerald-600 text-emerald-950",
      },
      {
        label: "Received Purchases",
        value: purchases.filter((purchase) => purchase.status === "RECEIVED")
          .length,
        icon: PackageCheck,
        iconClass: "from-violet-200 to-violet-600 text-violet-950",
      },
      {
        label: "Pending Purchases",
        value: purchases.filter((purchase) => purchase.status === "PENDING")
          .length,
        icon: Clock,
        iconClass: "from-amber-200 to-amber-500 text-amber-950",
      },
    ],
    [purchases],
  );
  const closeDrawer = () => {
    setDrawer(null);
    setSelectedPurchase(null);
  };
  const openView = (purchase) => {
    setOpenMenuId(null);
    setSelectedPurchase(purchase);
    setDrawer("view");
  };
  const openEdit = (purchase) => {
    setOpenMenuId(null);
    setSelectedPurchase(purchase);
    setDrawer("edit");
  };
  const markReceived = (purchase) => {
  setOpenMenuId(null);
  setMobileActionPurchase(null);

  handleStatusChange(purchase.purchase_id, "RECEIVED");
 };
  const savePurchase = (payload) => createPurchase.mutate(payload);
  const saveEdit = (payload) => {
  updatePurchase.mutate({
    purchaseId: selectedPurchase.purchase_id,
    payload,
  });
};
  const drawerSuppliers = Array.isArray(suppliersQuery.data)
    ? suppliersQuery.data
    : [];
  const drawerProducts = Array.isArray(productsQuery.data)
    ? productsQuery.data
    : [];

  return (
    <div className="space-y-5 pb-8">
      <header className="flex flex-col gap-4 2xl:flex-row 2xl:items-center 2xl:justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-white">
          Purchases
        </h1>
        <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4 2xl:w-[1040px] 2xl:grid-cols-12">
          <label className="relative min-w-0 sm:col-span-2 2xl:col-span-3">
            <Search
              size={17}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search purchase"
              className="h-11 w-full rounded-xl border border-white/10 bg-slate-900/70 pl-10 pr-3 text-sm text-slate-100 shadow-sm backdrop-blur-xl outline-none transition placeholder:text-slate-500 focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/20"
            />
          </label>
          <AppSelect
            value={supplierFilter}
            onValueChange={setSupplierFilter}
            options={[
              { value: "ALL", label: "All suppliers" },
              ...supplierOptions,
            ]}
            ariaLabel="Filter by supplier"
            className="2xl:col-span-2"
          />
          <AppSelect
            value={statusFilter}
            onValueChange={setStatusFilter}
            options={[
              { value: "ALL", label: "All statuses" },
              ...purchaseStatuses,
            ]}
            ariaLabel="Filter by status"
            className="2xl:col-span-2"
          />
          <div className="grid grid-cols-2 gap-2 2xl:col-span-3">
            <label className="sr-only" htmlFor="purchase-from">
              From date
            </label>
            <input
              id="purchase-from"
              type="date"
              value={fromDate}
              max={toDate || undefined}
              onChange={(event) => setFromDate(event.target.value)}
              className={inputClass}
            />
            <label className="sr-only" htmlFor="purchase-to">
              To date
            </label>
            <input
              id="purchase-to"
              type="date"
              value={toDate}
              min={fromDate || undefined}
              onChange={(event) => setToDate(event.target.value)}
              className={inputClass}
            />
          </div>
          <Button
            className="h-11 w-full sm:col-span-2 2xl:col-span-2"
            onClick={() => setDrawer("add")}
          >
            <Plus size={17} />
            Add Purchase
          </Button>
        </div>
      </header>
      {purchasesQuery.isPending ? (
        <SummarySkeleton />
      ) : (
        <section
          className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Purchase statistics"
        >
          {summary.map(({ label, value, icon: Icon, iconClass }) => (
            <Card
              key={label}
              className="min-h-[92px] rounded-3xl"
              padding="p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-slate-400">{label}</p>
                  <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                    {value}
                  </p>
                </div>
                <span
                  className={`grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br ${iconClass}`}
                >
                  <Icon size={18} />
                </span>
              </div>
            </Card>
          ))}
        </section>
      )}
      {purchasesQuery.isPending ? (
        <PurchaseTableSkeleton />
      ) : purchasesQuery.isError ? (
        <Card padding="p-5">
          <div className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-red-400/25 bg-red-400/5 p-4 sm:flex-row sm:items-center">
            <p className="text-sm text-red-200">Unable to load purchases.</p>
            <Button variant="outline" onClick={purchasesQuery.refetch}>
              Try again
            </Button>
          </div>
        </Card>
      ) : filteredPurchases.length ? (
        <>
          <div className="hidden max-h-[660px] overflow-auto rounded-3xl border border-white/10 bg-slate-950/35 shadow-[0_0_40px_rgba(16,185,129,0.08)] md:block">
            <table className="w-full min-w-[1120px] border-separate border-spacing-y-2 px-2 text-left text-sm">
              <thead className="sticky top-0 z-20 bg-slate-900/95 text-xs uppercase tracking-wider text-slate-400 backdrop-blur-xl">
                <tr>
                  {[
                    "Purchase ID",
                    "Supplier",
                    "Invoice No",
                    "Purchase Date",
                    "Total Amount",
                    "Status",
                    "Items Count",
                    "Actions",
                  ].map((heading) => (
                    <th
                      key={heading}
                      className={`px-4 py-3 font-semibold ${heading === "Actions" ? "text-right" : ""}`}
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredPurchases.map((purchase) => (
                  <tr
                    key={purchase.purchase_id}
                    className="group bg-white/[0.025] transition-all hover:bg-emerald-400/[0.07] hover:shadow-[0_0_24px_rgba(16,185,129,0.12)]"
                  >
                    <td className="rounded-l-2xl px-4 py-3.5 font-semibold text-emerald-200">
                      #{purchase.purchase_id}
                    </td>
                    <td className="px-4 py-3.5 font-semibold text-white">
                      {purchase.supplier_name || "--"}
                    </td>
                    <td className="px-4 py-3.5 text-slate-400">
                      {purchase.supplier_invoice_no || "--"}
                    </td>
                    <td className="px-4 py-3.5 text-slate-300">
                      {dateText(purchase.purchase_date)}
                    </td>
                    <td className="px-4 py-3.5 font-semibold text-slate-100">
                      {currency(purchase.total_amount)}
                    </td>
                    <td className="px-4 py-3.5">
                      <StatusBadge status={purchase.status} />
                    </td>
                    <td className="px-4 py-3.5 text-slate-300">
                      {purchase.items?.length || 0}
                    </td>
                    <td className="rounded-r-2xl px-4 py-3.5">
                      <PurchaseActions
                        purchase={purchase}
                        openMenuId={openMenuId}
                        onToggle={setOpenMenuId}
                        onView={openView}
                        onEdit={openEdit}
                        onReceive={markReceived}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="space-y-3 md:hidden">
            {filteredPurchases.map((purchase) => (
              <Card
                key={purchase.purchase_id}
                className="rounded-3xl"
                padding="p-4"
              >
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-white">
                      {purchase.supplier_name || "--"}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {purchase.supplier_invoice_no || "--"}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setMobileActionPurchase(purchase)}
                    className="grid h-9 w-9 place-items-center rounded-xl text-slate-400 transition hover:bg-emerald-400/10 hover:text-emerald-200"
                    aria-label={`Actions for purchase ${purchase.purchase_id}`}
                  >
                    <MoreHorizontal size={18} />
                  </button>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3 border-t border-white/10 pt-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-slate-500">
                      Purchase ID
                    </p>
                    <p className="mt-1 text-sm font-semibold text-emerald-200">
                      #{purchase.purchase_id}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-slate-500">
                      Total Amount
                    </p>
                    <p className="mt-1 text-sm font-semibold text-slate-100">
                      {currency(purchase.total_amount)}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <p className="text-xs text-slate-400">
                    {dateText(purchase.purchase_date)} ·{" "}
                    {purchase.items?.length || 0} items
                  </p>
                  <StatusBadge status={purchase.status} />
                </div>
              </Card>
            ))}
          </div>
        </>
      ) : (
        <Card padding="p-6">
          <div className="flex min-h-64 flex-col items-center justify-center rounded-3xl border border-emerald-400/20 bg-emerald-400/[0.05] text-center">
            <span className="grid h-14 w-14 place-items-center rounded-2xl border border-emerald-300/20 bg-emerald-400/10 text-emerald-300">
              <ShoppingCart size={26} />
            </span>
            <p className="mt-4 font-semibold text-emerald-100">
              No purchases found
            </p>
            <Button className="mt-5" onClick={() => setDrawer("add")}>
              <Plus size={17} />
              Create Purchase
            </Button>
          </div>
        </Card>
      )}
      {drawer === "view" && (
        <Drawer
          title="Purchase Details"
          onClose={closeDrawer}
          widthClass="max-w-3xl"
        >
          <PurchaseDetails purchase={selectedPurchase} />
        </Drawer>
      )}
      {drawer === "add" && (
        <Drawer
          title="Add Purchase"
          onClose={closeDrawer}
          widthClass="max-w-4xl"
        >
          <PurchaseForm
            suppliers={drawerSuppliers}
            products={drawerProducts}
            onSave={savePurchase}
            onClose={closeDrawer}
            saving={createPurchase.isPending}
          />
        </Drawer>
      )}
      {drawer === "edit" && selectedPurchase && (
        <Drawer
          title="Edit Purchase"
          onClose={closeDrawer}
          widthClass="max-w-4xl"
        >
          <PurchaseForm
            suppliers={drawerSuppliers}
            products={drawerProducts}
            purchase={selectedPurchase}
            onSave={saveEdit}
            onClose={closeDrawer}
            saving={updatePurchase.isPending}
          />
        </Drawer>
      )}
      {mobileActionPurchase && (
        <div className="fixed inset-0 z-50 flex items-end bg-slate-950/70 p-3 backdrop-blur-sm md:hidden">
          <button
            type="button"
            className="absolute inset-0"
            aria-label="Close actions"
            onClick={() => setMobileActionPurchase(null)}
          />
          <div className="relative w-full rounded-3xl border border-white/10 bg-slate-900/95 p-3 shadow-2xl shadow-emerald-950/40">
            <p className="px-3 py-2 text-sm font-semibold text-white">
              Purchase #{mobileActionPurchase.purchase_id}
            </p>
            <button
              type="button"
              onClick={() => {
                setMobileActionPurchase(null);
                openView(mobileActionPurchase);
              }}
              className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-slate-200 transition hover:bg-emerald-400/10"
            >
              <Eye size={17} />
              View Purchase
            </button>
            {mobileActionPurchase.status !== "RECEIVED" && (
              <button
                type="button"
                onClick={() => {
                  setMobileActionPurchase(null);
                  openEdit(mobileActionPurchase);
                }}
                className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-slate-200 transition hover:bg-emerald-400/10"
              >
                <Pencil size={17} />
                Edit Purchase
              </button>
            )}
            {mobileActionPurchase.status === "PENDING" && (
              <button
                type="button"
                onClick={() => markReceived(mobileActionPurchase)}
                className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-emerald-300 transition hover:bg-emerald-400/10"
              >
                <PackageCheck size={17} />
                Mark as Received
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Purchases;

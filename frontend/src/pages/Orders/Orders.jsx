import { useEffect, useMemo, useState } from "react";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-toastify";
import {
  Clock3,
  Eye,
  IndianRupee,
  MoreHorizontal,
  Pencil,
  Plus,
  Save,
  Search,
  ShoppingBag,
  Trash2,
  Truck,
} from "lucide-react";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import AppSelect from "../../components/ui/AppSelect";
import Drawer from "../../components/ui/Drawer";
import api from "../../services/api";

const statusOptions = [
  { value: "PENDING", label: "Pending" },
  { value: "CONFIRMED", label: "Processing" },
  { value: "COMPLETED", label: "Delivered" },
  { value: "CANCELLED", label: "Cancelled" },
];
const blankItem = { product_id: "", packaging_id: "", quantity: 1 };
const today = new Date().toLocaleDateString("en-CA");
const inputClass =
  "h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10";

const number = (value) => Number(value) || 0;
const initials = (name = "") =>
  name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase() || "C";
const dateText = (value) =>
  value
    ? new Intl.DateTimeFormat("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }).format(new Date(`${value}T00:00:00`))
    : "--";
const displayStatus = (status) =>
  ({
    CONFIRMED: "Processing",
    PROCESSING: "Processing",
    COMPLETED: "Delivered",
    DELIVERED: "Delivered",
    PENDING: "Pending",
    CANCELLED: "Cancelled",
  })[status] ||
  status ||
  "Unknown";
const isDelivered = (status) =>
  status === "COMPLETED" || status === "DELIVERED";

function Skeleton({ className = "" }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-xl bg-emerald-300/10 ${className}`}
    />
  );
}

function StatusBadge({ status }) {
  const className = isDelivered(status)
    ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-300"
    : status === "CONFIRMED" || status === "PROCESSING"
      ? "border-cyan-400/25 bg-cyan-400/10 text-cyan-300"
      : status === "PENDING"
        ? "border-amber-400/25 bg-amber-400/10 text-amber-300"
        : status === "CANCELLED"
          ? "border-red-400/25 bg-red-400/10 text-red-300"
          : "border-slate-400/20 bg-slate-400/10 text-slate-300";
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${className}`}
    >
      {displayStatus(status)}
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

function OrdersTableSkeleton() {
  return (
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/35">
      <div className="grid min-w-[880px] grid-cols-[.7fr_1.8fr_1.2fr_.7fr_1fr_.45fr] gap-4 border-b border-white/10 bg-white/[0.05] px-5 py-4">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} className="h-3 w-16 bg-slate-400/10" />
        ))}
      </div>
      {Array.from({ length: 6 }, (_, row) => (
        <div
          key={row}
          className="grid min-w-[880px] grid-cols-[.7fr_1.8fr_1.2fr_.7fr_1fr_.45fr] items-center gap-4 border-b border-white/10 px-5 py-4 last:border-b-0"
        >
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-4 w-20 bg-slate-400/10" />
          ))}
        </div>
      ))}
    </div>
  );
}

function DrawerSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }, (_, index) => (
        <Skeleton key={index} className="h-14 w-full bg-white/[0.04]" />
      ))}
    </div>
  );
}

function OrderActions({
  order,
  openMenuId,
  onToggle,
  onView,
  onEdit,
  onCancel,
}) {
  const open = openMenuId === order.order_id;
  return (
    <div className="relative flex justify-end">
      <button
        type="button"
        onClick={() => onToggle(open ? null : order.order_id)}
        className="grid h-9 w-9 place-items-center rounded-xl border border-transparent text-slate-400 transition hover:border-emerald-300/25 hover:bg-emerald-400/10 hover:text-emerald-200"
        aria-label={`Actions for order ${order.order_id}`}
        aria-expanded={open}
      >
        <MoreHorizontal size={18} />
      </button>
      {open && (
        <div className="absolute right-0 top-10 z-30 w-40 rounded-2xl border border-white/15 bg-slate-900/95 p-1.5 shadow-2xl shadow-emerald-950/30 backdrop-blur-xl">
          <button
            type="button"
            onClick={() => onView(order)}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-emerald-400/10 hover:text-emerald-100"
          >
            <Eye size={15} />
            View Order
          </button>
          {!isDelivered(order.status) && (
            <button
              type="button"
              onClick={() => onEdit(order)}
              className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-emerald-400/10 hover:text-emerald-100"
            >
              <Pencil size={15} />
              Edit Order
            </button>
          )}
          <button
            type="button"
            onClick={() => onCancel(order)}
            disabled={isDelivered(order.status) || order.status === "CANCELLED"}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-red-300 transition hover:bg-red-400/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Trash2 size={15} />
            Cancel Order
          </button>
        </div>
      )}
    </div>
  );
}

function OrderDetails({ order }) {
  if (!order) return <DrawerSkeleton />;
  const details = [
    { label: "Order ID", value: `#${order.order_id}` },
    { label: "Customer", value: order.customer_name || "--" },
    { label: "Order Date", value: dateText(order.order_date) },
  ];
  return (
    <div className="space-y-5">
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Order Information
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {details.map((item) => (
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
          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3.5">
            <p className="text-[11px] uppercase tracking-wider text-slate-500">
              Status
            </p>
            <div className="mt-2">
              <StatusBadge status={order.status} />
            </div>
          </div>
          <div className="col-span-2 rounded-2xl border border-white/10 bg-white/[0.03] p-3.5">
            <p className="text-[11px] uppercase tracking-wider text-slate-500">
              Notes
            </p>
            <p className="mt-1 break-words text-sm font-semibold text-slate-100">
              {order.notes || "--"}
            </p>
          </div>
        </div>
      </section>
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Ordered Items
        </h3>
        <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.03]">
          <table className="min-w-[500px] w-full text-left text-xs">
            <thead className="bg-white/[0.05] uppercase tracking-wider text-slate-500">
              <tr>
                {["Product", "Packaging", "Quantity"].map((heading) => (
                  <th key={heading} className="px-4 py-3 font-semibold">
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {order.items?.map((item) => (
                <tr
                  key={
                    item.order_item_id ||
                    `${item.product_id}-${item.packaging_id}`
                  }
                  className="border-t border-white/10"
                >
                  <td className="px-4 py-3 font-semibold text-slate-100">
                    {item.product_name || "--"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 font-medium text-emerald-200">
                      {item.unit_name || "--"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{item.quantity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function OrderForm({ customers, products, order, onSave, onClose, saving }) {
  const defaults = order
    ? {
        customer_id: String(order.customer_id),
        order_date: order.order_date || today,
        status: order.status || "PENDING",
        notes: order.notes || "",
        items: order.items?.map((item) => ({
          product_id: String(item.product_id),
          packaging_id: String(item.packaging_id),
          quantity: item.quantity,
        })) || [blankItem],
      }
    : {
        customer_id: "",
        order_date: today,
        status: "PENDING",
        notes: "",
        items: [blankItem],
      };
  const { control, register, handleSubmit, watch, reset, setValue } = useForm({
    defaultValues: defaults,
  });
  const { fields, append, remove } = useFieldArray({ control, name: "items" });
  const items = watch("items") || [];
  const totalQuantity = useMemo(
    () => items.reduce((total, item) => total + number(item.quantity), 0),
    [items],
  );
  useEffect(() => {
    reset(defaults);
  }, [order, reset]);
  const customerOptions = customers
    .filter((customer) => customer.status !== "INACTIVE")
    .map((customer) => ({
      value: String(customer.customer_id),
      label: customer.customer_name,
    }));
  const productOptions = products
    .filter((product) => product.status !== "INACTIVE")
    .map((product) => ({
      value: String(product.product_id),
      label: product.product_name,
    }));
  const submit = (values) =>
    onSave({
      customer_id: Number(values.customer_id),
      order_date: values.order_date,
      status: values.status,
      notes: values.notes.trim() || null,
      items: values.items.map((item) => ({
        product_id: Number(item.product_id),
        packaging_id: Number(item.packaging_id),
        quantity: number(item.quantity),
      })),
    });
  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-5">
      <section>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Order Details
        </h3>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Customer
            </span>
            <Controller
              control={control}
              name="customer_id"
              rules={{ required: true }}
              render={({ field }) => (
                <AppSelect
                  value={field.value}
                  onValueChange={field.onChange}
                  options={customerOptions}
                  placeholder="Select customer"
                  ariaLabel="Customer"
                />
              )}
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Order Date
            </span>
            <input
              type="date"
              required
              {...register("order_date")}
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
                  options={statusOptions}
                  ariaLabel="Order status"
                />
              )}
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Notes
            </span>
            <textarea
              rows={1}
              {...register("notes")}
              className="w-full resize-none rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10"
            />
          </label>
        </div>
      </section>
      <section className="border-t border-white/10 pt-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="font-semibold text-white">Order Items</h3>
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
            const product = products.find(
              (item) =>
                String(item.product_id) === String(items[index]?.product_id),
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
                    aria-label="Remove order item"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
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
                  <label>
                    <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-slate-500">
                      Quantity
                    </span>
                    <input
                      type="number"
                      step="any"
                      min="0.001"
                      required
                      {...register(`items.${index}.quantity`, {
                        valueAsNumber: true,
                      })}
                      className={inputClass}
                    />
                  </label>
                </div>
              </div>
            );
          })}
        </div>
      </section>
      <section className="rounded-3xl border border-emerald-300/15 bg-emerald-400/[0.05] p-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Order Summary
        </h3>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-slate-500">
              Total Items
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-100">
              {items.length}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-slate-500">
              Total Quantity
            </p>
            <p className="mt-1 text-sm font-semibold text-slate-100">
              {totalQuantity}
            </p>
          </div>
        </div>
      </section>
      <div className="flex justify-end gap-3 border-t border-white/10 pt-5">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          <Save size={17} />
          {saving ? "Saving..." : order ? "Save Changes" : "Create Order"}
        </Button>
      </div>
    </form>
  );
}

function Orders() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [customerFilter, setCustomerFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [drawer, setDrawer] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [mobileActionOrder, setMobileActionOrder] = useState(null);
  const ordersQuery = useQuery({
    queryKey: ["orders"],
    queryFn: async () => (await api.get("/orders")).data,
  });
  const customersQuery = useQuery({
    queryKey: ["customers"],
    queryFn: async () => (await api.get("/customers")).data,
    enabled: drawer === "create" || drawer === "edit",
  });
  const productsQuery = useQuery({
    queryKey: ["products"],
    queryFn: async () => (await api.get("/products")).data,
    enabled: drawer === "create" || drawer === "edit",
  });
  const createOrder = useMutation({
    mutationFn: async (payload) => (await api.post("/orders", payload)).data,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["orders"] });
      toast.success(result.message || "Order created successfully");
      setDrawer(null);
    },
    onError: (error) =>
      toast.error(
        error?.response?.data?.detail ||
          "Unable to create order. Please try again.",
      ),
  });
  const orders = Array.isArray(ordersQuery.data) ? ordersQuery.data : [];
  const customerOptions = useMemo(
    () =>
      [
        ...new Map(
          orders
            .filter((order) => order.customer_id)
            .map((order) => [
              order.customer_id,
              order.customer_name || `Customer #${order.customer_id}`,
            ]),
        ).entries(),
      ].map(([value, label]) => ({ value: String(value), label })),
    [orders],
  );
  const filteredOrders = useMemo(() => {
    const term = search.trim().toLowerCase();
    return orders.filter((order) => {
      const matchesSearch =
        !term ||
        [order.customer_name, String(order.order_id)].some((value) =>
          value?.toLowerCase().includes(term),
        );
      const date = order.order_date || "";
      return (
        matchesSearch &&
        (customerFilter === "ALL" ||
          String(order.customer_id) === customerFilter) &&
        (statusFilter === "ALL" || order.status === statusFilter) &&
        (!fromDate || date >= fromDate) &&
        (!toDate || date <= toDate)
      );
    });
  }, [orders, search, customerFilter, statusFilter, fromDate, toDate]);
  const summary = useMemo(
    () => [
      {
        label: "Total Orders",
        value: orders.length,
        icon: ShoppingBag,
        iconClass: "from-sky-200 to-sky-600 text-sky-950",
      },
      {
        label: "Pending Orders",
        value: orders.filter((order) => order.status === "PENDING").length,
        icon: Clock3,
        iconClass: "from-amber-200 to-amber-500 text-amber-950",
      },
      {
        label: "Delivered Orders",
        value: orders.filter((order) => isDelivered(order.status)).length,
        icon: Truck,
        iconClass: "from-emerald-200 to-emerald-600 text-emerald-950",
      },
      {
        label: "Total Order Value",
        value: "--",
        icon: IndianRupee,
        iconClass: "from-violet-200 to-violet-600 text-violet-950",
      },
    ],
    [orders],
  );
  const closeDrawer = () => {
    setDrawer(null);
    setSelectedOrder(null);
  };
  const openView = (order) => {
    setOpenMenuId(null);
    setSelectedOrder(order);
    setDrawer("view");
  };
  const openEdit = (order) => {
    setOpenMenuId(null);
    setSelectedOrder(order);
    setDrawer("edit");
  };
  const cancelOrder = () => {
    setOpenMenuId(null);
    setMobileActionOrder(null);
    toast.info(
      "Order cancellation will be available when the order update API is connected.",
    );
  };
  const saveEdit = () =>
    toast.info(
      "Order editing will be available when the order update API is connected.",
    );
  const customers = Array.isArray(customersQuery.data)
    ? customersQuery.data
    : [];
  const products = Array.isArray(productsQuery.data) ? productsQuery.data : [];

  return (
    <div className="space-y-5 pb-8">
      <header className="flex flex-col gap-4 2xl:flex-row 2xl:items-center 2xl:justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-white">Orders</h1>
        <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4 2xl:w-[1040px] 2xl:grid-cols-12">
          <label className="relative min-w-0 sm:col-span-2 2xl:col-span-3">
            <Search
              size={17}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
            />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search order"
              className="h-11 w-full rounded-xl border border-white/10 bg-slate-900/70 pl-10 pr-3 text-sm text-slate-100 shadow-sm backdrop-blur-xl outline-none transition placeholder:text-slate-500 focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/20"
            />
          </label>
          <AppSelect
            value={customerFilter}
            onValueChange={setCustomerFilter}
            options={[
              { value: "ALL", label: "All customers" },
              ...customerOptions,
            ]}
            ariaLabel="Filter by customer"
            className="2xl:col-span-2"
          />
          <AppSelect
            value={statusFilter}
            onValueChange={setStatusFilter}
            options={[
              { value: "ALL", label: "All statuses" },
              ...statusOptions,
            ]}
            ariaLabel="Filter by status"
            className="2xl:col-span-2"
          />
          <div className="grid grid-cols-2 gap-2 2xl:col-span-3">
            <label className="sr-only" htmlFor="order-from">
              From date
            </label>
            <input
              id="order-from"
              type="date"
              value={fromDate}
              max={toDate || undefined}
              onChange={(event) => setFromDate(event.target.value)}
              className={inputClass}
            />
            <label className="sr-only" htmlFor="order-to">
              To date
            </label>
            <input
              id="order-to"
              type="date"
              value={toDate}
              min={fromDate || undefined}
              onChange={(event) => setToDate(event.target.value)}
              className={inputClass}
            />
          </div>
          <Button
            className="h-11 w-full sm:col-span-2 2xl:col-span-2"
            onClick={() => setDrawer("create")}
          >
            <Plus size={17} />
            Create Order
          </Button>
        </div>
      </header>
      {ordersQuery.isPending ? (
        <SummarySkeleton />
      ) : (
        <section
          className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Order statistics"
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
      {ordersQuery.isPending ? (
        <OrdersTableSkeleton />
      ) : ordersQuery.isError ? (
        <Card padding="p-5">
          <div className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-red-400/25 bg-red-400/5 p-4 sm:flex-row sm:items-center">
            <p className="text-sm text-red-200">Unable to load orders.</p>
            <Button variant="outline" onClick={ordersQuery.refetch}>
              Try again
            </Button>
          </div>
        </Card>
      ) : filteredOrders.length ? (
        <>
          <div className="hidden max-h-[660px] overflow-auto rounded-3xl border border-white/10 bg-slate-950/35 shadow-[0_0_40px_rgba(16,185,129,0.08)] md:block">
            <table className="w-full min-w-[880px] border-separate border-spacing-y-2 px-2 text-left text-sm">
              <thead className="sticky top-0 z-20 bg-slate-900/95 text-xs uppercase tracking-wider text-slate-400 backdrop-blur-xl">
                <tr>
                  {[
                    "Order ID",
                    "Customer",
                    "Order Date",
                    "Items",
                    "Status",
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
                {filteredOrders.map((order) => (
                  <tr
                    key={order.order_id}
                    className="group bg-white/[0.025] transition-all hover:bg-emerald-400/[0.07] hover:shadow-[0_0_24px_rgba(16,185,129,0.12)]"
                  >
                    <td className="rounded-l-2xl px-4 py-3.5 font-semibold text-emerald-200">
                      #{order.order_id}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-3">
                        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-emerald-300 to-teal-600 text-xs font-bold text-emerald-950">
                          {initials(order.customer_name)}
                        </span>
                        <p className="font-semibold text-white">
                          {order.customer_name || "--"}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-slate-300">
                      {dateText(order.order_date)}
                    </td>
                    <td className="px-4 py-3.5 text-slate-300">
                      {order.items?.length || 0}
                    </td>
                    <td className="px-4 py-3.5">
                      <StatusBadge status={order.status} />
                    </td>
                    <td className="rounded-r-2xl px-4 py-3.5">
                      <OrderActions
                        order={order}
                        openMenuId={openMenuId}
                        onToggle={setOpenMenuId}
                        onView={openView}
                        onEdit={openEdit}
                        onCancel={cancelOrder}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="space-y-3 md:hidden">
            {filteredOrders.map((order) => (
              <Card key={order.order_id} className="rounded-3xl" padding="p-4">
                <div className="flex items-start gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-gradient-to-br from-emerald-300 to-teal-600 text-sm font-bold text-emerald-950">
                    {initials(order.customer_name)}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold text-white">
                      {order.customer_name || "--"}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      Order #{order.order_id}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setMobileActionOrder(order)}
                    className="grid h-9 w-9 place-items-center rounded-xl text-slate-400 transition hover:bg-emerald-400/10 hover:text-emerald-200"
                    aria-label={`Actions for order ${order.order_id}`}
                  >
                    <MoreHorizontal size={18} />
                  </button>
                </div>
                <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-3">
                  <p className="text-xs text-slate-400">
                    {dateText(order.order_date)} · {order.items?.length || 0}{" "}
                    items
                  </p>
                  <StatusBadge status={order.status} />
                </div>
              </Card>
            ))}
          </div>
        </>
      ) : (
        <Card padding="p-6">
          <div className="flex min-h-64 flex-col items-center justify-center rounded-3xl border border-emerald-400/20 bg-emerald-400/[0.05] text-center">
            <span className="grid h-14 w-14 place-items-center rounded-2xl border border-emerald-300/20 bg-emerald-400/10 text-emerald-300">
              <ShoppingBag size={26} />
            </span>
            <p className="mt-4 font-semibold text-emerald-100">
              No orders found
            </p>
            <Button className="mt-5" onClick={() => setDrawer("create")}>
              <Plus size={17} />
              Create Order
            </Button>
          </div>
        </Card>
      )}
      {drawer === "view" && (
        <Drawer title="Order Details" onClose={closeDrawer}>
          <OrderDetails order={selectedOrder} />
        </Drawer>
      )}
      {drawer === "create" && (
        <Drawer
          title="Create Order"
          onClose={closeDrawer}
          widthClass="max-w-4xl"
        >
          {customersQuery.isPending || productsQuery.isPending ? (
            <DrawerSkeleton />
          ) : (
            <OrderForm
              customers={customers}
              products={products}
              onSave={createOrder.mutate}
              onClose={closeDrawer}
              saving={createOrder.isPending}
            />
          )}
        </Drawer>
      )}
      {drawer === "edit" && selectedOrder && (
        <Drawer title="Edit Order" onClose={closeDrawer} widthClass="max-w-4xl">
          {customersQuery.isPending || productsQuery.isPending ? (
            <DrawerSkeleton />
          ) : (
            <OrderForm
              customers={customers}
              products={products}
              order={selectedOrder}
              onSave={saveEdit}
              onClose={closeDrawer}
            />
          )}
        </Drawer>
      )}
      {mobileActionOrder && (
        <div className="fixed inset-0 z-50 flex items-end bg-slate-950/70 p-3 backdrop-blur-sm md:hidden">
          <button
            type="button"
            className="absolute inset-0"
            aria-label="Close actions"
            onClick={() => setMobileActionOrder(null)}
          />
          <div className="relative w-full rounded-3xl border border-white/10 bg-slate-900/95 p-3 shadow-2xl shadow-emerald-950/40">
            <p className="px-3 py-2 text-sm font-semibold text-white">
              Order #{mobileActionOrder.order_id}
            </p>
            <button
              type="button"
              onClick={() => {
                setMobileActionOrder(null);
                openView(mobileActionOrder);
              }}
              className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-slate-200 transition hover:bg-emerald-400/10"
            >
              <Eye size={17} />
              View Order
            </button>
            {!isDelivered(mobileActionOrder.status) && (
              <button
                type="button"
                onClick={() => {
                  setMobileActionOrder(null);
                  openEdit(mobileActionOrder);
                }}
                className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-slate-200 transition hover:bg-emerald-400/10"
              >
                <Pencil size={17} />
                Edit Order
              </button>
            )}
            <button
              type="button"
              onClick={() => cancelOrder(mobileActionOrder)}
              disabled={
                isDelivered(mobileActionOrder.status) ||
                mobileActionOrder.status === "CANCELLED"
              }
              className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-red-300 transition hover:bg-red-400/10 disabled:opacity-40"
            >
              <Trash2 size={17} />
              Cancel Order
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Orders;

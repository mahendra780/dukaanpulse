import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { toast } from "react-toastify";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Barcode,
  Boxes,
  CheckCircle2,
  Eye,
  Layers3,
  MoreHorizontal,
  Package,
  Pencil,
  Plus,
  Power,
  Save,
  Search,
  Tag,
  X,
} from "lucide-react";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import AppSelect from "../../components/ui/AppSelect";
import api from "../../services/api";
import { getLowStockProducts } from "../../services/dashboardService";

const numberFormatter = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
});

function formatNumber(value) {
  return typeof value === "number" ? numberFormatter.format(value) : "—";
}

function SkeletonBlock({ className = "" }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-emerald-300/10 ${className}`}
      aria-hidden="true"
    />
  );
}

function getStockState(product) {
  const stock = Number(product.current_stock) || 0;
  const reorderLevel = Number(product.reorder_level);
  const hasReorderLevel =
    product.reorder_level !== null &&
    product.reorder_level !== undefined &&
    Number.isFinite(reorderLevel);

  if (stock <= 0)
    return {
      label: "Critical",
      className: "border-red-400/25 bg-red-400/10 text-red-300",
    };
  if (hasReorderLevel && stock <= reorderLevel)
    return {
      label: "Low",
      className: "border-amber-400/25 bg-amber-400/10 text-amber-300",
    };
  return {
    label: "Healthy",
    className: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
  };
}

function StatusBadge({ status }) {
  const isActive = status === "ACTIVE";
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${isActive ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-300" : "border-red-400/25 bg-red-400/10 text-red-300"}`}
    >
      {isActive ? "Active" : "Inactive"}
    </span>
  );
}

function StockBadge({ product }) {
  const stockState = getStockState(product);
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${stockState.className}`}
    >
      {stockState.label}
    </span>
  );
}

function ProductsTableSkeleton() {
  return (
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/35">
      <div className="grid min-w-[980px] grid-cols-[1.75fr_1fr_1fr_1fr_1fr_.8fr_.8fr_.45fr] gap-4 border-b border-white/10 bg-white/[0.05] px-5 py-4">
        {Array.from({ length: 8 }, (_, index) => (
          <SkeletonBlock key={index} className="h-3 w-16 bg-slate-400/10" />
        ))}
      </div>
      {Array.from({ length: 6 }, (_, row) => (
        <div
          key={row}
          className="grid min-w-[980px] grid-cols-[1.75fr_1fr_1fr_1fr_1fr_.8fr_.8fr_.45fr] items-center gap-4 border-b border-white/10 px-5 py-4 last:border-b-0"
        >
          {Array.from({ length: 8 }, (_, index) => (
            <SkeletonBlock key={index} className="h-4 w-20 bg-slate-400/10" />
          ))}
        </div>
      ))}
    </div>
  );
}

function StatsSkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: 4 }, (_, index) => (
        <SkeletonBlock
          key={index}
          className="h-[92px] rounded-3xl bg-white/[0.04]"
        />
      ))}
    </div>
  );
}

function ActionMenu({
  product,
  openMenuId,
  onToggle,
  onView,
  onEdit,
  onDeactivate,
  isUpdating,
}) {
  const isOpen = openMenuId === product.product_id;

  return (
    <div className="relative flex justify-end">
      <button
        type="button"
        onClick={() => onToggle(isOpen ? null : product.product_id)}
        className="grid h-9 w-9 place-items-center rounded-xl border border-transparent text-slate-400 transition hover:border-emerald-300/25 hover:bg-emerald-400/10 hover:text-emerald-200"
        aria-label={`Actions for ${product.product_name}`}
        aria-expanded={isOpen}
      >
        <MoreHorizontal size={18} aria-hidden="true" />
      </button>
      {isOpen && (
        <div className="absolute right-0 top-10 z-30 w-44 rounded-2xl border border-white/15 bg-slate-900/95 p-1.5 shadow-2xl shadow-emerald-950/30 backdrop-blur-xl">
          <button
            type="button"
            onClick={() => onView(product)}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-emerald-400/10 hover:text-emerald-100"
          >
            <Eye size={15} />
            View Details
          </button>
          <button
            type="button"
            onClick={() => onEdit(product)}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-emerald-400/10 hover:text-emerald-100"
          >
            <Pencil size={15} />
            Edit Product
          </button>
          <button
            type="button"
            onClick={() => onDeactivate(product)}
            disabled={product.status === "INACTIVE" || isUpdating}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-red-300 transition hover:bg-red-400/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Power size={15} />
            Deactivate Product
          </button>
        </div>
      )}
    </div>
  );
}

function Drawer({ title, children, onClose, widthClass = "max-w-md" }) {
  return (
    <div className="fixed inset-0 z-50">
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm"
        aria-label="Close drawer"
        onClick={onClose}
      />
      <motion.aside
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        transition={{ duration: 0.24, ease: "easeOut" }}
        className={`absolute inset-y-0 right-0 flex w-full ${widthClass} flex-col border-l border-white/10 bg-slate-900/95 shadow-2xl shadow-emerald-950/40 backdrop-blur-2xl`}
      >
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4 sm:px-6">
          <h2 className="font-semibold text-white">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="grid h-9 w-9 place-items-center rounded-xl text-slate-400 transition hover:bg-emerald-400/10 hover:text-emerald-200"
            aria-label="Close drawer"
          >
            <X size={19} />
          </button>
        </div>
        <div className="scrollbar-thin flex-1 overflow-y-auto p-5 sm:p-6">
          {children}
        </div>
      </motion.aside>
    </div>
  );
}

function DetailDrawerContent({ product, isPending, isError, onRetry }) {
  if (isPending)
    return (
      <div className="space-y-5">
        {Array.from({ length: 6 }, (_, index) => (
          <SkeletonBlock key={index} className="h-16 w-full bg-white/[0.05]" />
        ))}
      </div>
    );
  if (isError)
    return (
      <div className="rounded-2xl border border-red-400/25 bg-red-400/5 p-4">
        <p className="text-sm text-red-200">Unable to load product details.</p>
        <Button className="mt-4" variant="outline" onClick={onRetry}>
          Try again
        </Button>
      </div>
    );
  if (!product) return null;

  return (
    <div className="space-y-5">
      <div className="rounded-3xl border border-emerald-300/15 bg-emerald-400/[0.05] p-5">
        <div className="flex items-start justify-between gap-3">
          <Package className="text-emerald-300" size={24} />
          <StatusBadge status={product.status} />
        </div>
        <h3 className="mt-5 text-xl font-bold tracking-tight text-white">
          {product.product_name}
        </h3>
        <p className="mt-1 text-sm text-slate-400">
          {product.brand_name || "No brand"}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {[
          {
            label: "Current Stock",
            value: `${formatNumber(product.current_stock)} ${product.base_unit || "units"}`,
            icon: Boxes,
          },
          {
            label: "Category",
            value: product.category || "Uncategorized",
            icon: Tag,
          },
          { label: "Brand", value: product.brand_name || "—", icon: Package },
          { label: "SKU", value: product.sku || "—", icon: Barcode },
        ].map(({ label, value, icon: Icon }) => (
          <div
            key={label}
            className="rounded-2xl border border-white/10 bg-white/[0.03] p-3.5"
          >
            <Icon size={16} className="text-emerald-300" aria-hidden="true" />
            <p className="mt-3 text-[11px] uppercase tracking-wider text-slate-500">
              {label}
            </p>
            <p className="mt-1 break-words text-sm font-semibold text-slate-100">
              {value}
            </p>
          </div>
        ))}
      </div>
      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Packaging Units
        </p>
        <div className="flex flex-wrap gap-2">
          {product.packaging?.length ? (
            product.packaging.map((packaging) => (
              <span
                key={packaging.packaging_id}
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${packaging.is_base_unit ? "border-emerald-300/25 bg-emerald-400/10 text-emerald-200" : "border-white/10 bg-white/[0.04] text-slate-300"}`}
              >
                {packaging.unit_name}
                {packaging.is_base_unit
                  ? " · Base"
                  : ` · ${formatNumber(packaging.conversion_to_base)} base`}
              </span>
            ))
          ) : (
            <p className="text-sm text-slate-500">
              No packaging units available.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function AddProductDrawer({ categories, onClose, onSave, isSaving }) {
  const { control, handleSubmit, register } = useForm({
    defaultValues: {
      product_name: "",
      brand_name: "",
      sku: "",
      category_id: "",
      status: "ACTIVE",
      packaging: [
        {
          unit_name: "",
          conversion_to_base: 1,
          is_base_unit: true,
          is_purchase_unit: false,
          is_sale_unit: false,
        },
      ],
    },
  });
  const { fields, append, remove } = useFieldArray({
    control,
    name: "packaging",
  });

  return (
    <Drawer title="Add Product" onClose={onClose} widthClass="max-w-[520px]">
      <form onSubmit={handleSubmit(onSave)} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block sm:col-span-2">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Product Name
            </span>
            <input
              {...register("product_name")}
              required
              className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10"
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Brand Name
            </span>
            <input
              {...register("brand_name")}
              className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10"
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              SKU
            </span>
            <input
              {...register("sku")}
              required
              className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10"
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-slate-300">
              Category
            </span>
            <Controller
              control={control}
              name="category_id"
              rules={{ required: true }}
              render={({ field }) => (
                <AppSelect
                  value={field.value}
                  onValueChange={field.onChange}
                  options={categories.map((category) => ({
                    value: String(category.category_id),
                    label: category.category_name,
                  }))}
                  placeholder="Select category"
                  ariaLabel="Category"
                />
              )}
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
                  options={[
                    { value: "ACTIVE", label: "Active" },
                    { value: "INACTIVE", label: "Inactive" },
                  ]}
                  ariaLabel="Status"
                />
              )}
            />
          </label>
        </div>

        <section className="border-t border-white/10 pt-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="font-semibold text-white">Packaging</h3>
            <button
              type="button"
              onClick={() =>
                append({
                  unit_name: "",
                  conversion_to_base: 1,
                  is_base_unit: false,
                  is_purchase_unit: false,
                  is_sale_unit: false,
                })
              }
              className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-300/25 bg-emerald-400/10 px-3 py-2 text-xs font-semibold text-emerald-200 transition hover:bg-emerald-400/20"
            >
              <Plus size={15} />
              Add Unit
            </button>
          </div>
          <div className="space-y-3">
            {fields.map((field, index) => (
              <div
                key={field.id}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-3.5"
              >
                <div className="grid grid-cols-[1fr_108px_auto] gap-2">
                  <label>
                    <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-slate-500">
                      Unit Name
                    </span>
                    <input
                      {...register(`packaging.${index}.unit_name`)}
                      required
                      className="h-10 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50"
                    />
                  </label>
                  <label>
                    <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-wider text-slate-500">
                      Conversion
                    </span>
                    <input
                      {...register(`packaging.${index}.conversion_to_base`, {
                        valueAsNumber: true,
                      })}
                      required
                      min="0.0001"
                      step="any"
                      type="number"
                      className="h-10 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => remove(index)}
                    disabled={fields.length === 1}
                    className="mt-[25px] grid h-10 w-10 place-items-center rounded-xl text-slate-500 transition hover:bg-red-400/10 hover:text-red-300 disabled:cursor-not-allowed disabled:opacity-30"
                    aria-label="Remove packaging unit"
                  >
                    <X size={17} />
                  </button>
                </div>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
                  {[
                    ["is_base_unit", "Base Unit"],
                    ["is_purchase_unit", "Purchase Unit"],
                    ["is_sale_unit", "Sale Unit"],
                  ].map(([name, label]) => (
                    <label
                      key={name}
                      className="inline-flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-300"
                    >
                      <input
                        type="checkbox"
                        {...register(`packaging.${index}.${name}`)}
                        className="h-4 w-4 rounded border-white/20 bg-slate-950 text-emerald-500 focus:ring-emerald-400"
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        <div className="flex justify-end gap-3 border-t border-white/10 pt-5">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" className="w-full" disabled={isSaving}>
            <Save size={17} />
            {isSaving ? "Saving..." : "Save Product"}
          </Button>
        </div>
      </form>
    </Drawer>
  );
}

function Products() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [openMenuId, setOpenMenuId] = useState(null);
  const [drawer, setDrawer] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [formValues, setFormValues] = useState({
    product_name: "",
    brand_name: "",
    sku: "",
    category_id: "",
    status: "ACTIVE",
  });

  const productsQuery = useQuery({
    queryKey: ["products"],
    queryFn: async () => (await api.get("/products")).data,
  });
  const categoriesQuery = useQuery({
    queryKey: ["categories"],
    queryFn: async () => (await api.get("/categories")).data,
    staleTime: 5 * 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });
  const lowStockQuery = useQuery({
    queryKey: ["dashboard", "low-stock"],
    queryFn: async () => (await getLowStockProducts()).data,
  });
  const detailsQuery = useQuery({
    queryKey: ["products", selectedProduct?.product_id],
    queryFn: async () =>
      (await api.get(`/products/${selectedProduct.product_id}`)).data,
    enabled: drawer === "details" && Boolean(selectedProduct?.product_id),
  });
  const updateProduct = useMutation({
    mutationFn: async ({ productId, payload }) =>
      (await api.patch(`/products/${productId}`, payload)).data,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.removeQueries({ queryKey: ["products", result.product_id] });
      toast.success(result.message || "Product updated successfully");
      setDrawer(null);
      setSelectedProduct(null);
    },
    onError: (error) =>
      toast.error(
        error?.response?.data?.detail ||
          "Unable to update product. Please try again.",
      ),
  });
  const createProduct = useMutation({
    mutationFn: async (payload) => (await api.post("/products", payload)).data,
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["products"] });
      await queryClient.invalidateQueries({
        queryKey: ["dashboard", "low-stock"],
      });
      toast.success(result.message || "Product created successfully");
      closeDrawer();
    },
    onError: (error) =>
      toast.error(
        error?.response?.data?.detail ||
          "Unable to create product. Please try again.",
      ),
  });

  const products = Array.isArray(productsQuery.data) ? productsQuery.data : [];
  const categories = useMemo(
    () =>
      (Array.isArray(categoriesQuery.data) ? categoriesQuery.data : []).filter(
        (category) => category.status === "ACTIVE",
      ),
    [categoriesQuery.data],
  );
  const filteredProducts = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return products.filter((product) => {
      const matchesSearch =
        !normalizedSearch ||
        [product.product_name, product.brand_name, product.sku].some((value) =>
          value?.toLowerCase().includes(normalizedSearch),
        );
      return (
        matchesSearch &&
        (categoryFilter === "ALL" || product.category === categoryFilter) &&
        (statusFilter === "ALL" || product.status === statusFilter)
      );
    });
  }, [products, search, categoryFilter, statusFilter]);
  const statistics = useMemo(() => {
    const lowStockValue = lowStockQuery.isPending
      ? null
      : Array.isArray(lowStockQuery.data)
        ? lowStockQuery.data.length
        : "—";
    return [
      {
        label: "Total Products",
        value: products.length,
        icon: Package,
        iconClass: "bg-sky-400/10 text-sky-300",
      },
      {
        label: "Active Products",
        value: products.filter((product) => product.status === "ACTIVE").length,
        icon: CheckCircle2,
        iconClass: "bg-emerald-400/10 text-emerald-300",
      },
      {
        label: "Categories",
        value: categories.length,
        icon: Layers3,
        iconClass: "bg-violet-400/10 text-violet-300",
      },
      {
        label: "Low Stock Products",
        value: lowStockValue,
        isLoading: lowStockQuery.isPending,
        icon: AlertTriangle,
        iconClass: "bg-amber-400/10 text-amber-300",
      },
    ];
  }, [products, categories, lowStockQuery.data, lowStockQuery.isPending]);

  useEffect(() => {
    if (drawer === "edit" && selectedProduct)
      setFormValues({
        product_name: selectedProduct.product_name || "",
        brand_name: selectedProduct.brand_name || "",
        sku: selectedProduct.sku || "",
        category_id: String(
          categories.find(
            (category) => category.category_name === selectedProduct.category,
          )?.category_id || "",
        ),
        status: selectedProduct.status || "ACTIVE",
      });
  }, [drawer, selectedProduct, categories]);

  const closeDrawer = () => {
    setDrawer(null);
    setSelectedProduct(null);
  };
  const openDetails = (product) => {
    setOpenMenuId(null);
    setSelectedProduct(product);
    setDrawer("details");
  };
  const openEdit = (product) => {
    setOpenMenuId(null);
    setSelectedProduct(product);
    setDrawer("edit");
  };
  const deactivateProduct = (product) => {
    setOpenMenuId(null);
    updateProduct.mutate({
      productId: product.product_id,
      payload: { status: "INACTIVE" },
    });
  };
  const submitProduct = (values) => {
    createProduct.mutate({
      ...values,
      category_id: Number(values.category_id),
      packaging: values.packaging.map((packaging) => ({
        ...packaging,
        conversion_to_base: Number(packaging.conversion_to_base),
      })),
    });
  };
  
  const submitEdit = (event) => {
    event.preventDefault();
    if (selectedProduct)
      updateProduct.mutate({
        productId: selectedProduct.product_id,
        payload: formValues,
      });
  };
  const renderActions = (product) => (
    <ActionMenu
      product={product}
      openMenuId={openMenuId}
      onToggle={setOpenMenuId}
      onView={openDetails}
      onEdit={openEdit}
      onDeactivate={deactivateProduct}
      isUpdating={updateProduct.isPending}
    />
  );

  return (
    <div className="space-y-5 pb-8">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-white">
          Products
        </h1>
        <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2 xl:w-[760px] xl:grid-cols-12">
          <label className="relative min-w-0 sm:col-span-2 xl:col-span-5">
            <Search
              size={17}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
              aria-hidden="true"
            />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search products"
              className="h-11 w-full rounded-xl border border-white/10 bg-slate-900/70 pl-10 pr-3 text-sm text-slate-100 shadow-sm backdrop-blur-xl outline-none transition placeholder:text-slate-500 focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/20"
              aria-label="Search products"
            />
          </label>
          <AppSelect
            value={categoryFilter}
            onValueChange={setCategoryFilter}
            options={[
              { value: "ALL", label: "All categories" },
              ...categories.map((category) => ({
                value: category.category_name,
                label: category.category_name,
              })),
            ]}
            ariaLabel="Filter by category"
            className="xl:col-span-2"
          />
          <AppSelect
            value={statusFilter}
            onValueChange={setStatusFilter}
            options={[
              { value: "ALL", label: "All statuses" },
              { value: "ACTIVE", label: "Active" },
              { value: "INACTIVE", label: "Inactive" },
            ]}
            ariaLabel="Filter by status"
            className="xl:col-span-2"
          />
          <Button
            className="h-11 w-full px-3.5 py-2 sm:col-span-2 xl:col-span-3"
            onClick={() => setDrawer("add")}
          >
            <Plus size={17} />
            Add Product
          </Button>
        </div>
      </header>

      {productsQuery.isPending ? (
        <StatsSkeleton />
      ) : (
        <section
          className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
          aria-label="Product statistics"
        >
          {statistics.map(
            ({ label, value, isLoading, icon: Icon, iconClass }) => (
              <Card
                key={label}
                className="min-h-[92px] rounded-3xl"
                padding="p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm text-slate-400">{label}</p>
                    {isLoading ? (
                      <SkeletonBlock className="mt-3 h-7 w-12" />
                    ) : (
                      <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                        {typeof value === "number"
                          ? formatNumber(value)
                          : value}
                      </p>
                    )}
                  </div>
                  <span
                    className={`grid h-9 w-9 place-items-center rounded-xl ${iconClass}`}
                  >
                    <Icon size={18} aria-hidden="true" />
                  </span>
                </div>
              </Card>
            ),
          )}
        </section>
      )}

      {productsQuery.isPending ? (
        <ProductsTableSkeleton />
      ) : productsQuery.isError ? (
        <Card padding="p-5">
          <div className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-red-400/25 bg-red-400/5 p-4 sm:flex-row sm:items-center">
            <p className="text-sm text-red-200">Unable to load products.</p>
            <Button variant="outline" onClick={productsQuery.refetch}>
              Try again
            </Button>
          </div>
        </Card>
      ) : filteredProducts.length ? (
        <>
          <div className="hidden overflow-auto rounded-3xl border border-white/10 bg-slate-950/35 shadow-[0_0_40px_rgba(16,185,129,0.08)] md:block md:max-h-[660px]">
            <table className="min-w-[1020px] w-full border-separate border-spacing-y-2 px-2 text-left text-sm">
              <thead className="sticky top-0 z-20 bg-slate-900/95 text-xs uppercase tracking-wider text-slate-400 backdrop-blur-xl">
                <tr>
                  <th className="px-4 py-3 font-semibold">Product</th>
                  <th className="hidden px-4 py-3 font-semibold lg:table-cell">
                    Brand
                  </th>
                  <th className="px-4 py-3 font-semibold">SKU</th>
                  <th className="hidden px-4 py-3 font-semibold xl:table-cell">
                    Category
                  </th>
                  <th className="px-4 py-3 font-semibold">Stock</th>
                  <th className="hidden px-4 py-3 font-semibold lg:table-cell">
                    Base Unit
                  </th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 text-right font-semibold">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((product) => (
                  <tr
                    key={product.product_id}
                    className="group rounded-2xl bg-white/[0.025] transition-all hover:bg-emerald-400/[0.07] hover:shadow-[0_0_24px_rgba(16,185,129,0.12)]"
                  >
                    <td className="rounded-l-2xl px-4 py-3.5">
                      <p className="font-semibold text-white">
                        {product.product_name}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {product.brand_name || "No brand"}
                      </p>
                    </td>
                    <td className="hidden px-4 py-3.5 text-slate-300 lg:table-cell">
                      {product.brand_name || "—"}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-400">
                      {product.sku || "—"}
                    </td>
                    <td className="hidden px-4 py-3.5 text-slate-300 xl:table-cell">
                      {product.category || "Uncategorized"}
                    </td>
                    <td className="px-4 py-3.5">
                      <p className="whitespace-nowrap font-semibold text-slate-100">
                        {formatNumber(product.current_stock)}{" "}
                        <span className="font-normal text-slate-500">
                          {product.base_unit || "units"}
                        </span>
                      </p>
                      <span className="mt-1.5 inline-flex">
                        <StockBadge product={product} />
                      </span>
                    </td>
                    <td className="hidden px-4 py-3.5 text-slate-300 lg:table-cell">
                      {product.base_unit || "—"}
                    </td>
                    <td className="px-4 py-3.5">
                      <StatusBadge status={product.status} />
                    </td>
                    <td className="rounded-r-2xl px-4 py-3.5">
                      {renderActions(product)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="space-y-3 md:hidden">
            {filteredProducts.map((product) => (
              <Card
                key={product.product_id}
                className="rounded-3xl"
                padding="p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-white">
                      {product.product_name}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {product.brand_name || "No brand"}
                    </p>
                  </div>
                  {renderActions(product)}
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3 border-t border-white/10 pt-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-slate-500">
                      Stock
                    </p>
                    <p className="mt-1 font-semibold text-slate-100">
                      {formatNumber(product.current_stock)}{" "}
                      {product.base_unit || "units"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] uppercase tracking-wider text-slate-500">
                      SKU
                    </p>
                    <p className="mt-1 truncate font-mono text-sm text-slate-300">
                      {product.sku || "—"}
                    </p>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <StockBadge product={product} />
                  <StatusBadge status={product.status} />
                </div>
              </Card>
            ))}
          </div>
        </>
      ) : (
        <Card padding="p-6">
          <div className="flex min-h-64 flex-col items-center justify-center rounded-3xl border border-emerald-400/20 bg-emerald-400/[0.05] text-center">
            <span className="grid h-14 w-14 place-items-center rounded-2xl border border-emerald-300/20 bg-emerald-400/10 text-emerald-300">
              <Package size={26} aria-hidden="true" />
            </span>
            <p className="mt-4 font-semibold text-emerald-100">
              No products found
            </p>
          </div>
        </Card>
      )}

      {drawer === "add" && (
        <AddProductDrawer
          categories={categories}
          onClose={closeDrawer}
          onSave={submitProduct}
          isSaving={createProduct.isPending}
        />
      )}
      {drawer === "details" && (
        <Drawer title="Product Details" onClose={closeDrawer}>
          <DetailDrawerContent
            product={detailsQuery.data}
            isPending={detailsQuery.isPending}
            isError={detailsQuery.isError}
            onRetry={detailsQuery.refetch}
          />
        </Drawer>
      )}
      {drawer === "edit" && selectedProduct && (
        <Drawer title="Edit Product" onClose={closeDrawer}>
          <form onSubmit={submitEdit} className="space-y-5">
            {[
              { name: "product_name", label: "Product Name" },
              { name: "brand_name", label: "Brand" },
              { name: "sku", label: "SKU" },
            ].map(({ name, label }) => (
              <label key={name} className="block">
                <span className="mb-2 block text-sm font-medium text-slate-300">
                  {label}
                </span>
                <input
                  required={name !== "brand_name"}
                  value={formValues[name]}
                  onChange={(event) =>
                    setFormValues((current) => ({
                      ...current,
                      [name]: event.target.value,
                    }))
                  }
                  className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10"
                />
              </label>
            ))}
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-300">
                Status
              </span>
              <AppSelect
                value={formValues.status}
                onValueChange={(status) =>
                  setFormValues((current) => ({ ...current, status }))
                }
                options={[
                  { value: "ACTIVE", label: "Active" },
                  { value: "INACTIVE", label: "Inactive" },
                ]}
                ariaLabel="Status"
              />
            </label>
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-slate-300">
                Category
              </span>
              <AppSelect
                value={formValues.category_id}
                onValueChange={(category_id) =>
                  setFormValues((current) => ({ ...current, category_id }))
                }
                options={categories.map((category) => ({
                  value: String(category.category_id),
                  label: category.category_name,
                }))}
                placeholder="Select category"
                ariaLabel="Category"
              />
            </label>
            <Button
              type="submit"
              className="w-full"
              disabled={updateProduct.isPending}
            >
              <Save size={17} />
              {updateProduct.isPending ? "Saving…" : "Save Changes"}
            </Button>
          </form>
        </Drawer>
      )}
    </div>
  );
}

export default Products;

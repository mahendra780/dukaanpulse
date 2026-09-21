import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Controller, useForm } from 'react-hook-form'
import { toast } from 'react-toastify'
import {
  CheckCircle2,
  CircleDollarSign,
  CreditCard,
  Eye,
  MapPin,
  MoreHorizontal,
  Pencil,
  Phone,
  Plus,
  Power,
  Save,
  Search,
  UserRound,
  Users,
  WalletCards,
} from 'lucide-react'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import AppSelect from '../../components/ui/AppSelect'
import Drawer from '../../components/ui/Drawer'
import api from '../../services/api'

const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

function formatCurrency(value) {
  return currencyFormatter.format(Number(value) || 0)
}

function paymentTerms(days) {
  return `${Number(days) || 0} Days`
}

function customerInitials(name = '') {
  return name.split(' ').filter(Boolean).slice(0, 2).map((word) => word[0]).join('').toUpperCase() || 'C'
}

function SkeletonBlock({ className = '' }) {
  return <div className={`animate-pulse rounded-lg bg-emerald-300/10 ${className}`} aria-hidden="true" />
}

function StatusBadge({ status }) {
  const isActive = status === 'ACTIVE'
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${isActive ? 'border-emerald-400/25 bg-emerald-400/10 text-emerald-300' : 'border-red-400/25 bg-red-400/10 text-red-300'}`}>{isActive ? 'Active' : 'Inactive'}</span>
}

function SummarySkeleton() {
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }, (_, index) => <SkeletonBlock key={index} className="h-[92px] rounded-3xl bg-white/[0.04]" />)}</div>
}

function CustomerTableSkeleton() {
  return (
    <div className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/35">
      <div className="grid min-w-[900px] grid-cols-[2fr_1fr_1fr_1fr_1fr_.8fr_.4fr] gap-4 border-b border-white/10 bg-white/[0.05] px-5 py-4">{Array.from({ length: 7 }, (_, index) => <SkeletonBlock key={index} className="h-3 w-16 bg-slate-400/10" />)}</div>
      {Array.from({ length: 6 }, (_, row) => <div key={row} className="grid min-w-[900px] grid-cols-[2fr_1fr_1fr_1fr_1fr_.8fr_.4fr] items-center gap-4 border-b border-white/10 px-5 py-4 last:border-b-0">{Array.from({ length: 7 }, (_, index) => <SkeletonBlock key={index} className="h-4 w-20 bg-slate-400/10" />)}</div>)}
    </div>
  )
}

function CustomerActionMenu({ customer, openMenuId, onToggle, onView, onEdit, onDeactivate, isUpdating }) {
  const isOpen = openMenuId === customer.customer_id

  return (
    <div className="relative flex justify-end">
      <button type="button" onClick={() => onToggle(isOpen ? null : customer.customer_id)} className="grid h-9 w-9 place-items-center rounded-xl border border-transparent text-slate-400 transition hover:border-emerald-300/25 hover:bg-emerald-400/10 hover:text-emerald-200" aria-label={`Actions for ${customer.customer_name}`} aria-expanded={isOpen}><MoreHorizontal size={18} /></button>
      {isOpen && <div className="absolute right-0 top-10 z-30 w-44 rounded-2xl border border-white/15 bg-slate-900/95 p-1.5 shadow-2xl shadow-emerald-950/30 backdrop-blur-xl"><button type="button" onClick={() => onView(customer)} className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-emerald-400/10 hover:text-emerald-100"><Eye size={15} />View Customer</button><button type="button" onClick={() => onEdit(customer)} className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-emerald-400/10 hover:text-emerald-100"><Pencil size={15} />Edit Customer</button><button type="button" onClick={() => onDeactivate(customer)} disabled={customer.status === 'INACTIVE' || isUpdating} className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-red-300 transition hover:bg-red-400/10 disabled:cursor-not-allowed disabled:opacity-40"><Power size={15} />Deactivate Customer</button></div>}
    </div>
  )
}

function CustomerDetails({ customer, isPending, isError, onRetry }) {
  if (isPending) return <div className="space-y-4">{Array.from({ length: 5 }, (_, index) => <SkeletonBlock key={index} className="h-20 w-full bg-white/[0.04]" />)}</div>
  if (isError) return <div className="rounded-2xl border border-red-400/25 bg-red-400/5 p-4"><p className="text-sm text-red-200">Unable to load customer details.</p><Button className="mt-4" variant="outline" onClick={onRetry}>Try again</Button></div>
  if (!customer) return null

  return (
    <div className="space-y-5">
      <section className="rounded-3xl border border-emerald-300/15 bg-emerald-400/[0.05] p-5"><div className="flex items-start justify-between gap-3"><span className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-emerald-300 to-teal-600 text-emerald-950"><span className="font-bold">{customerInitials(customer.customer_name)}</span></span><StatusBadge status={customer.status} /></div><h3 className="mt-5 text-xl font-bold tracking-tight text-white">{customer.customer_name}</h3><p className="mt-1 text-sm text-slate-400">{customer.phone || 'No phone number'}</p></section>
      <section><h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Customer Info</h3><div className="grid grid-cols-2 gap-3">{[{ label: 'Phone', value: customer.phone || '—', icon: Phone }, { label: 'Area', value: customer.area || '—', icon: MapPin }, { label: 'Address', value: customer.address || '—', icon: MapPin, span: true }].map(({ label, value, icon: Icon, span }) => <div key={label} className={`rounded-2xl border border-white/10 bg-white/[0.03] p-3.5 ${span ? 'col-span-2' : ''}`}><Icon size={16} className="text-emerald-300" /><p className="mt-3 text-[11px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-1 break-words text-sm font-semibold text-slate-100">{value}</p></div>)}</div></section>
      <section><h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Credit Details</h3><div className="grid grid-cols-2 gap-3">{[{ label: 'Credit Limit', value: formatCurrency(customer.credit_limit), icon: CircleDollarSign }, { label: 'Payment Terms', value: paymentTerms(customer.payment_terms_days), icon: CreditCard }, { label: 'Outstanding Balance', value: '—', icon: WalletCards, span: true }].map(({ label, value, icon: Icon, span }) => <div key={label} className={`rounded-2xl border border-white/10 bg-white/[0.03] p-3.5 ${span ? 'col-span-2' : ''}`}><Icon size={16} className="text-emerald-300" /><p className="mt-3 text-[11px] uppercase tracking-wider text-slate-500">{label}</p><p className="mt-1 text-sm font-semibold text-slate-100">{value}</p></div>)}</div></section>
      <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-4"><h3 className="font-semibold text-white">Purchase History</h3><p className="mt-3 text-sm text-slate-500">Coming in Phase 7</p></section>
    </div>
  )
}

function AddCustomerDrawer({ onClose, onSave, saving }) {
  const { control, handleSubmit, register } = useForm({ defaultValues: { customer_name: '', phone: '', area: '', address: '', credit_limit: 0, payment_terms_days: 0, status: 'ACTIVE' } })

  return (
    <Drawer title="Add Customer" onClose={onClose} widthClass="max-w-[520px]">
      <form onSubmit={handleSubmit((values) => onSave({ ...values, phone: values.phone || null, credit_limit: Number(values.credit_limit), payment_terms_days: Number(values.payment_terms_days) }))} className="space-y-4">
        {[{ name: 'customer_name', label: 'Customer Name', required: true }, { name: 'phone', label: 'Phone' }, { name: 'area', label: 'Area', required: true }].map(({ name, label, required }) => <label key={name} className="block"><span className="mb-2 block text-sm font-medium text-slate-300">{label}</span><input {...register(name)} required={required} className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10" /></label>)}
        <label className="block"><span className="mb-2 block text-sm font-medium text-slate-300">Address</span><textarea {...register('address')} required rows={3} className="w-full resize-none rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10" /></label>
        <div className="grid grid-cols-2 gap-3"><label className="block"><span className="mb-2 block text-sm font-medium text-slate-300">Credit Limit</span><input {...register('credit_limit', { valueAsNumber: true })} min="0" type="number" className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50" /></label><label className="block"><span className="mb-2 block text-sm font-medium text-slate-300">Payment Terms</span><input {...register('payment_terms_days', { valueAsNumber: true })} min="0" type="number" className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50" /></label></div>
        <label className="block"><span className="mb-2 block text-sm font-medium text-slate-300">Status</span><Controller control={control} name="status" render={({ field }) => <AppSelect value={field.value} onValueChange={field.onChange} options={[{ value: 'ACTIVE', label: 'Active' }, { value: 'INACTIVE', label: 'Inactive' }]} ariaLabel="Status" />} /></label>
        <div className="flex justify-end gap-3 border-t border-white/10 pt-5"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" disabled={saving}><Save size={17} />{saving ? 'Saving…' : 'Save Customer'}</Button></div>
      </form>
    </Drawer>
  )
}

function Customers() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [areaFilter, setAreaFilter] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [drawer, setDrawer] = useState(null)
  const [selectedCustomer, setSelectedCustomer] = useState(null)
  const [openMenuId, setOpenMenuId] = useState(null)
  const [mobileActionCustomer, setMobileActionCustomer] = useState(null)
  const [formValues, setFormValues] = useState({})

  const customersQuery = useQuery({ queryKey: ['customers'], queryFn: async () => (await api.get('/customers')).data })
  const detailQuery = useQuery({ queryKey: ['customers', selectedCustomer?.customer_id], queryFn: async () => (await api.get(`/customers/${selectedCustomer.customer_id}`)).data, enabled: drawer === 'details' && Boolean(selectedCustomer?.customer_id) })
  const createCustomer = useMutation({
    mutationFn: async (payload) => (await api.post('/customers', payload)).data,
    onSuccess: async (result) => { await queryClient.invalidateQueries({ queryKey: ['customers'] }); toast.success(result.customer_name ? 'Customer created successfully' : 'Customer created'); setDrawer(null) },
    onError: (error) => toast.error(error?.response?.data?.detail || 'Unable to create customer. Please try again.'),
  })
  const updateCustomer = useMutation({
    mutationFn: async ({ customerId, payload }) => (await api.patch(`/customers/${customerId}`, payload)).data,
    onSuccess: async (result) => { await queryClient.invalidateQueries({ queryKey: ['customers'] }); queryClient.removeQueries({ queryKey: ['customers', result.customer_id] }); toast.success(result.message || 'Customer updated successfully'); setDrawer(null); setSelectedCustomer(null) },
    onError: (error) => toast.error(error?.response?.data?.detail || 'Unable to update customer. Please try again.'),
  })

  const customers = Array.isArray(customersQuery.data) ? customersQuery.data : []
  const areas = useMemo(() => [...new Set(customers.map((customer) => customer.area).filter(Boolean))].sort(), [customers])
  const filteredCustomers = useMemo(() => {
    const term = search.trim().toLowerCase()
    return customers.filter((customer) => {
      const matchesSearch = !term || [customer.customer_name, customer.phone, customer.area].some((value) => value?.toLowerCase().includes(term))
      return matchesSearch && (areaFilter === 'ALL' || customer.area === areaFilter) && (statusFilter === 'ALL' || customer.status === statusFilter)
    })
  }, [customers, search, areaFilter, statusFilter])
  const summary = useMemo(() => [
    { label: 'Total Customers', value: customers.length, icon: Users, iconClass: 'from-sky-200 to-sky-600 text-sky-950' },
    { label: 'Active Customers', value: customers.filter((customer) => customer.status === 'ACTIVE').length, icon: CheckCircle2, iconClass: 'from-emerald-200 to-emerald-600 text-emerald-950' },
    { label: 'Total Areas', value: areas.length, icon: MapPin, iconClass: 'from-violet-200 to-violet-600 text-violet-950' },
    { label: 'Credit Customers', value: customers.filter((customer) => Number(customer.credit_limit) > 0).length, icon: CreditCard, iconClass: 'from-amber-200 to-amber-500 text-amber-950' },
  ], [customers, areas])

  useEffect(() => {
    if (drawer === 'edit' && selectedCustomer) setFormValues({ customer_name: selectedCustomer.customer_name || '', phone: selectedCustomer.phone || '', area: selectedCustomer.area || '', address: selectedCustomer.address || '', credit_limit: selectedCustomer.credit_limit ?? 0, payment_terms_days: selectedCustomer.payment_terms_days ?? 0, status: selectedCustomer.status || 'ACTIVE' })
  }, [drawer, selectedCustomer])

  const closeDrawer = () => { setDrawer(null); setSelectedCustomer(null) }
  const openDetails = (customer) => { setOpenMenuId(null); setSelectedCustomer(customer); setDrawer('details') }
  const openEdit = (customer) => { setOpenMenuId(null); setSelectedCustomer(customer); setDrawer('edit') }
  const deactivateCustomer = (customer) => { setOpenMenuId(null); setMobileActionCustomer(null); updateCustomer.mutate({ customerId: customer.customer_id, payload: { status: 'INACTIVE' } }) }
  const submitEdit = (event) => { event.preventDefault(); if (selectedCustomer) updateCustomer.mutate({ customerId: selectedCustomer.customer_id, payload: { ...formValues, credit_limit: Number(formValues.credit_limit), payment_terms_days: Number(formValues.payment_terms_days) } }) }
  const renderActions = (customer) => <CustomerActionMenu customer={customer} openMenuId={openMenuId} onToggle={setOpenMenuId} onView={openDetails} onEdit={openEdit} onDeactivate={deactivateCustomer} isUpdating={updateCustomer.isPending} />

  return (
    <div className="space-y-5 pb-8">
      <header className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between"><h1 className="text-2xl font-bold tracking-tight text-white">Customers</h1><div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2 xl:w-[760px] xl:grid-cols-12"><label className="relative min-w-0 sm:col-span-2 xl:col-span-5"><Search size={17} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search customer" className="h-11 w-full rounded-xl border border-white/10 bg-slate-900/70 pl-10 pr-3 text-sm text-slate-100 shadow-sm backdrop-blur-xl outline-none transition placeholder:text-slate-500 focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/20" /></label><AppSelect value={areaFilter} onValueChange={setAreaFilter} options={[{ value: 'ALL', label: 'All areas' }, ...areas.map((area) => ({ value: area, label: area }))]} ariaLabel="Filter by area" className="xl:col-span-2" /><AppSelect value={statusFilter} onValueChange={setStatusFilter} options={[{ value: 'ALL', label: 'All statuses' }, { value: 'ACTIVE', label: 'Active' }, { value: 'INACTIVE', label: 'Inactive' }]} ariaLabel="Filter by status" className="xl:col-span-2" /><Button className="h-11 w-full sm:col-span-2 xl:col-span-3" onClick={() => setDrawer('add')}><Plus size={17} />Add Customer</Button></div></header>

      {customersQuery.isPending ? <SummarySkeleton /> : <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Customer statistics">{summary.map(({ label, value, icon: Icon, iconClass }) => <Card key={label} className="min-h-[92px] rounded-3xl" padding="p-4"><div className="flex items-start justify-between gap-3"><div><p className="text-sm text-slate-400">{label}</p><p className="mt-2 text-2xl font-bold tracking-tight text-white">{value}</p></div><span className={`grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br ${iconClass}`}><Icon size={18} /></span></div></Card>)}</section>}

      {customersQuery.isPending ? <CustomerTableSkeleton /> : customersQuery.isError ? <Card padding="p-5"><div className="flex flex-col items-start justify-between gap-4 rounded-2xl border border-red-400/25 bg-red-400/5 p-4 sm:flex-row sm:items-center"><p className="text-sm text-red-200">Unable to load customers.</p><Button variant="outline" onClick={customersQuery.refetch}>Try again</Button></div></Card> : filteredCustomers.length ? <><div className="hidden overflow-auto rounded-3xl border border-white/10 bg-slate-950/35 shadow-[0_0_40px_rgba(16,185,129,0.08)] md:block md:max-h-[660px]"><table className="min-w-[960px] w-full border-separate border-spacing-y-2 px-2 text-left text-sm"><thead className="sticky top-0 z-20 bg-slate-900/95 text-xs uppercase tracking-wider text-slate-400 backdrop-blur-xl"><tr><th className="px-4 py-3 font-semibold">Customer</th><th className="px-4 py-3 font-semibold">Phone</th><th className="px-4 py-3 font-semibold">Area</th><th className="hidden px-4 py-3 font-semibold lg:table-cell">Credit Limit</th><th className="hidden px-4 py-3 font-semibold lg:table-cell">Payment Terms</th><th className="px-4 py-3 font-semibold">Status</th><th className="px-4 py-3 text-right font-semibold">Actions</th></tr></thead><tbody>{filteredCustomers.map((customer) => <tr key={customer.customer_id} className="group bg-white/[0.025] transition-all hover:bg-emerald-400/[0.07] hover:shadow-[0_0_24px_rgba(16,185,129,0.12)]"><td className="rounded-l-2xl px-4 py-3.5"><div className="flex items-center gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-emerald-300 to-teal-600 text-xs font-bold text-emerald-950">{customerInitials(customer.customer_name)}</span><div className="min-w-0"><p className="font-semibold text-white">{customer.customer_name}</p><p className="mt-0.5 truncate text-xs text-slate-500">{customer.address || 'No address'}</p></div></div></td><td className="px-4 py-3.5 text-slate-300">{customer.phone || '—'}</td><td className="px-4 py-3.5 text-slate-300">{customer.area || '—'}</td><td className="hidden px-4 py-3.5 font-semibold text-slate-100 lg:table-cell">{formatCurrency(customer.credit_limit)}</td><td className="hidden px-4 py-3.5 text-slate-300 lg:table-cell">{paymentTerms(customer.payment_terms_days)}</td><td className="px-4 py-3.5"><StatusBadge status={customer.status} /></td><td className="rounded-r-2xl px-4 py-3.5">{renderActions(customer)}</td></tr>)}</tbody></table></div><div className="space-y-3 md:hidden">{filteredCustomers.map((customer) => <Card key={customer.customer_id} className="rounded-3xl" padding="p-4"><div className="flex items-start gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-gradient-to-br from-emerald-300 to-teal-600 text-sm font-bold text-emerald-950">{customerInitials(customer.customer_name)}</span><div className="min-w-0 flex-1"><p className="truncate font-semibold text-white">{customer.customer_name}</p><p className="mt-1 truncate text-sm text-slate-500">{customer.address || 'No address'}</p></div><button type="button" onClick={() => setMobileActionCustomer(customer)} className="grid h-9 w-9 place-items-center rounded-xl text-slate-400 transition hover:bg-emerald-400/10 hover:text-emerald-200" aria-label={`Actions for ${customer.customer_name}`}><MoreHorizontal size={18} /></button></div><div className="mt-4 grid grid-cols-2 gap-3 border-t border-white/10 pt-3"><div><p className="text-[11px] uppercase tracking-wider text-slate-500">Phone</p><p className="mt-1 text-sm font-medium text-slate-200">{customer.phone || '—'}</p></div><div><p className="text-[11px] uppercase tracking-wider text-slate-500">Credit Limit</p><p className="mt-1 text-sm font-medium text-slate-200">{formatCurrency(customer.credit_limit)}</p></div></div><div className="mt-3 flex items-center justify-between"><p className="text-xs text-slate-400">{paymentTerms(customer.payment_terms_days)}</p><StatusBadge status={customer.status} /></div></Card>)}</div></> : <Card padding="p-6"><div className="flex min-h-64 flex-col items-center justify-center rounded-3xl border border-emerald-400/20 bg-emerald-400/[0.05] text-center"><span className="grid h-14 w-14 place-items-center rounded-2xl border border-emerald-300/20 bg-emerald-400/10 text-emerald-300"><UserRound size={26} /></span><p className="mt-4 font-semibold text-emerald-100">No customers found</p><Button className="mt-5" onClick={() => setDrawer('add')}><Plus size={17} />Add Customer</Button></div></Card>}

      {drawer === 'add' && <AddCustomerDrawer onClose={closeDrawer} onSave={createCustomer.mutate} saving={createCustomer.isPending} />}
      {drawer === 'details' && <Drawer title="Customer Details" onClose={closeDrawer}><CustomerDetails customer={detailQuery.data} isPending={detailQuery.isPending} isError={detailQuery.isError} onRetry={detailQuery.refetch} /></Drawer>}
      {drawer === 'edit' && selectedCustomer && <Drawer title="Edit Customer" onClose={closeDrawer}><form onSubmit={submitEdit} className="space-y-4">{[{ name: 'customer_name', label: 'Customer Name', required: true }, { name: 'phone', label: 'Phone' }, { name: 'area', label: 'Area', required: true }].map(({ name, label, required }) => <label key={name} className="block"><span className="mb-2 block text-sm font-medium text-slate-300">{label}</span><input required={required} value={formValues[name]} onChange={(event) => setFormValues((current) => ({ ...current, [name]: event.target.value }))} className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10" /></label>)}<label className="block"><span className="mb-2 block text-sm font-medium text-slate-300">Address</span><textarea required rows={3} value={formValues.address} onChange={(event) => setFormValues((current) => ({ ...current, address: event.target.value }))} className="w-full resize-none rounded-xl border border-white/10 bg-slate-950/50 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/10" /></label><div className="grid grid-cols-2 gap-3"><label className="block"><span className="mb-2 block text-sm font-medium text-slate-300">Credit Limit</span><input min="0" type="number" value={formValues.credit_limit} onChange={(event) => setFormValues((current) => ({ ...current, credit_limit: event.target.value }))} className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50" /></label><label className="block"><span className="mb-2 block text-sm font-medium text-slate-300">Payment Terms</span><input min="0" type="number" value={formValues.payment_terms_days} onChange={(event) => setFormValues((current) => ({ ...current, payment_terms_days: event.target.value }))} className="h-11 w-full rounded-xl border border-white/10 bg-slate-950/50 px-3 text-sm text-slate-100 outline-none transition focus:border-emerald-400/50" /></label></div><label className="block"><span className="mb-2 block text-sm font-medium text-slate-300">Status</span><AppSelect value={formValues.status} onValueChange={(status) => setFormValues((current) => ({ ...current, status }))} options={[{ value: 'ACTIVE', label: 'Active' }, { value: 'INACTIVE', label: 'Inactive' }]} ariaLabel="Status" /></label><Button type="submit" className="mt-2 w-full" disabled={updateCustomer.isPending}><Save size={17} />{updateCustomer.isPending ? 'Saving…' : 'Save Changes'}</Button></form></Drawer>}
      {mobileActionCustomer && <div className="fixed inset-0 z-50 flex items-end bg-slate-950/70 p-3 backdrop-blur-sm md:hidden"><button type="button" className="absolute inset-0" aria-label="Close actions" onClick={() => setMobileActionCustomer(null)} /><div className="relative w-full rounded-3xl border border-white/10 bg-slate-900/95 p-3 shadow-2xl shadow-emerald-950/40"><p className="px-3 py-2 text-sm font-semibold text-white">{mobileActionCustomer.customer_name}</p><button type="button" onClick={() => { setMobileActionCustomer(null); openDetails(mobileActionCustomer) }} className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-slate-200 transition hover:bg-emerald-400/10"><Eye size={17} />View Customer</button><button type="button" onClick={() => { setMobileActionCustomer(null); openEdit(mobileActionCustomer) }} className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-slate-200 transition hover:bg-emerald-400/10"><Pencil size={17} />Edit Customer</button><button type="button" disabled={mobileActionCustomer.status === 'INACTIVE' || updateCustomer.isPending} onClick={() => deactivateCustomer(mobileActionCustomer)} className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-red-300 transition hover:bg-red-400/10 disabled:opacity-40"><Power size={17} />Deactivate Customer</button></div></div>}
    </div>
  )
}

export default Customers

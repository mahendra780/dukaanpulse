function Loader({ label = 'Loading...', className = '' }) {
  return (
    <div className={`flex items-center justify-center gap-3 py-8 text-sm text-[#94A3B8] ${className}`} role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/10 border-t-emerald-400" />
      <span>{label}</span>
    </div>
  )
}

export default Loader

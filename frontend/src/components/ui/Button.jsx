function Button({
  children,
  variant = 'primary',
  className = '',
  type = 'button',
  ...props
}) {
  const variants = {
    primary:
      'border border-emerald-300/30 bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-lg shadow-emerald-950/30 hover:from-emerald-400 hover:to-teal-400 hover:shadow-emerald-900/40 focus:ring-emerald-400',
    secondary:
      'border border-white/10 bg-white/5 text-slate-100 shadow-lg shadow-slate-950/10 backdrop-blur-xl hover:border-emerald-400/40 hover:bg-white/10 hover:shadow-emerald-950/20 focus:ring-emerald-400',
    outline:
      'border border-emerald-400/60 bg-transparent text-emerald-200 hover:border-emerald-300 hover:bg-emerald-400/10 hover:text-emerald-100 focus:ring-emerald-400',
    danger:
      'border border-red-300/20 bg-gradient-to-r from-red-500 to-rose-600 text-white shadow-lg shadow-red-950/30 hover:from-red-400 hover:to-rose-500 hover:shadow-red-900/40 focus:ring-red-400',
    ghost: 'text-[#94A3B8] hover:bg-white/10 hover:text-emerald-200 focus:ring-emerald-400',
  }

  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#0B1120] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:active:scale-100 ${variants[variant] || variants.primary} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export default Button

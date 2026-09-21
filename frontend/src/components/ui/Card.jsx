function GlassCard({
  children,
  className = '',
  padding = 'p-5',
  gradientBorder = false,
  ...props
}) {
  const glassSurface = `bg-slate-800/50 ${padding} backdrop-blur-xl`

  return (
    <section
      className={`group relative rounded-3xl transition-all duration-300 hover:shadow-[0_0_40px_rgba(16,185,129,0.15)] ${
        gradientBorder
          ? 'bg-gradient-to-br from-emerald-400/70 via-teal-400/20 to-violet-500/70 p-px'
          : `border border-white/10 ${glassSurface} hover:border-emerald-400/40`
      } ${className}`}
      {...props}
    >
      {gradientBorder ? (
        <div className={`h-full rounded-[calc(1.5rem-1px)] ${glassSurface}`}>
          {children}
        </div>
      ) : children}
    </section>
  )
}

export { GlassCard }
export default GlassCard

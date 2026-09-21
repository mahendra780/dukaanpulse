import { Search, X } from 'lucide-react'

function SearchBar({ value = '', onChange, onClear, placeholder = 'Search...', className = '', ...props }) {
  return (
    <div className={`relative ${className}`}>
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
      <input
        type="search"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full rounded-xl border border-white/10 bg-slate-800/50 py-2 pl-9 pr-9 text-sm text-slate-100 outline-none backdrop-blur-xl transition focus:border-emerald-400/60 focus:ring-2 focus:ring-emerald-400/15"
        {...props}
      />
      {value && onClear && (
        <button
          type="button"
          onClick={onClear}
          aria-label="Clear search"
          className="absolute right-2 top-1/2 grid h-6 w-6 -translate-y-1/2 place-items-center rounded-lg text-slate-500 hover:bg-white/10 hover:text-emerald-300"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}

export default SearchBar

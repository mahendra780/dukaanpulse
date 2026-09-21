import { Building2, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import logo from '../../assets/logo.svg'
import { navigationItems } from './navigation'

function Sidebar({ isOpen, onClose }) {
  return (
    <>
      {isOpen && (
        <button
          aria-label="Close sidebar overlay"
          className="fixed inset-0 z-30 bg-slate-950/80 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed bottom-4 left-4 top-4 z-40 flex w-72 -translate-x-[calc(100%+1rem)] flex-col rounded-[30px] border border-white/10 bg-[rgba(2,6,23,0.8)] text-slate-300 shadow-2xl shadow-black/40 backdrop-blur-xl transition-transform duration-300 lg:translate-x-0 ${isOpen ? 'translate-x-0' : ''}`}
        aria-label="Main navigation"
      >
        <div className="flex h-24 items-center justify-between border-b border-white/10 px-6">
          <NavLink to="/" className="flex items-center gap-3" onClick={onClose}>
            <span className="rounded-2xl border border-emerald-300/20 bg-emerald-400/10 p-1 shadow-lg shadow-emerald-950/30">
              <img src={logo} alt="DukaanPulse" className="h-10 w-10" />
            </span>
            <div>
              <p className="text-base font-bold tracking-tight text-[#F9FAFB]">DukaanPulse</p>
              <p className="mt-0.5 text-xs text-[#94A3B8]">Business ERP</p>
            </div>
          </NavLink>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close sidebar"
            className="rounded-xl p-2 text-[#94A3B8] transition hover:bg-white/10 hover:text-emerald-300 lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="scrollbar-thin flex-1 overflow-y-auto px-4 py-5">
          <p className="mb-3 px-3 text-[11px] font-bold uppercase tracking-widest text-slate-500">Workspace</p>
          <ul className="space-y-1.5">
            {navigationItems.map(({ label, path, icon: Icon }) => (
              <li key={path}>
                <NavLink
                  to={path}
                  end={path === '/'}
                  onClick={onClose}
                  className={({ isActive }) => `flex items-center gap-3 rounded-2xl px-3.5 py-3 text-sm font-medium transition-all duration-300 ${
                    isActive
                      ? 'bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-lg shadow-emerald-950/40'
                      : 'text-slate-400 hover:bg-emerald-400/10 hover:text-emerald-200 hover:shadow-[0_0_24px_rgba(16,185,129,0.12)]'
                  }`}
                >
                  <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                  <span>{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className="border-t border-white/10 p-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-3.5 backdrop-blur-xl">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-emerald-400/25 to-teal-400/15 text-emerald-300">
                <Building2 className="h-4.5 w-4.5" aria-hidden="true" />
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-100">DukaanPulse</p>
                <p className="truncate text-xs text-[#94A3B8]">Wholesale workspace</p>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2 border-t border-white/10 pt-3 text-xs text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]" />
              System operational
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}

export default Sidebar

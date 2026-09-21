import { Bell, CalendarDays, Menu, Search } from 'lucide-react'

function Navbar({ title, onMenuClick }) {
  return (
    <header className="sticky top-4 z-20 mx-4 flex h-16 items-center justify-between rounded-3xl border border-white/10 bg-slate-900/55 px-4 shadow-xl shadow-black/10 backdrop-blur-xl sm:mx-6 sm:px-5 lg:mx-8 lg:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-xl p-2 text-[#94A3B8] transition hover:bg-white/10 hover:text-emerald-300 lg:hidden"
          aria-label="Open sidebar"
        >
          <Menu className="h-6 w-6" />
        </button>
        <h1 className="truncate text-lg font-bold tracking-tight text-[#F9FAFB] sm:text-xl">{title}</h1>
      </div>

      <div className="flex items-center gap-1.5 sm:gap-3">
        <button type="button" aria-label="Search" className="rounded-xl p-2.5 text-[#94A3B8] transition hover:bg-white/10 hover:text-emerald-300">
          <Search className="h-5 w-5" />
        </button>
        <button type="button" aria-label="Notifications" className="relative rounded-xl p-2.5 text-[#94A3B8] transition hover:bg-white/10 hover:text-emerald-300">
          <Bell className="h-5 w-5" />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-emerald-400 ring-2 ring-slate-900" />
        </button>
        <button type="button" aria-label="Calendar" className="rounded-xl p-2.5 text-[#94A3B8] transition hover:bg-white/10 hover:text-emerald-300">
          <CalendarDays className="h-5 w-5" />
        </button>
        <button type="button" aria-label="User account" className="ml-1 grid h-10 w-10 place-items-center rounded-full border border-emerald-400/40 bg-gradient-to-br from-emerald-400 to-teal-500 text-sm font-bold text-slate-950 shadow-lg shadow-emerald-950/30 ring-2 ring-[#0B1120]">
          U
        </button>
      </div>
    </header>
  )
}

export default Navbar

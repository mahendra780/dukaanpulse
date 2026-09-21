import { motion } from 'framer-motion'
import { X } from 'lucide-react'

function Drawer({ title, children, onClose, widthClass = 'max-w-md' }) {
  return (
    <div className="fixed inset-0 z-50">
      <button type="button" className="absolute inset-0 bg-slate-950/70 backdrop-blur-sm" aria-label="Close drawer" onClick={onClose} />
      <motion.aside initial={{ x: '100%' }} animate={{ x: 0 }} transition={{ duration: 0.24, ease: 'easeOut' }} className={`absolute inset-y-0 right-0 flex w-full ${widthClass} flex-col border-l border-white/10 bg-slate-900/95 shadow-2xl shadow-emerald-950/40 backdrop-blur-2xl`}>
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4 sm:px-6">
          <h2 className="font-semibold text-white">{title}</h2>
          <button type="button" onClick={onClose} className="grid h-9 w-9 place-items-center rounded-xl text-slate-400 transition hover:bg-emerald-400/10 hover:text-emerald-200" aria-label="Close drawer"><X size={19} /></button>
        </div>
        <div className="scrollbar-thin flex-1 overflow-y-auto p-5 sm:p-6">{children}</div>
      </motion.aside>
    </div>
  )
}

export default Drawer

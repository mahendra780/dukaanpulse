import * as Select from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'

function AppSelect({
  value,
  onValueChange,
  options = [],
  placeholder = 'Select an option',
  disabled = false,
  className = '',
  ariaLabel,
}) {
  return (
    <Select.Root value={value || undefined} onValueChange={onValueChange} disabled={disabled}>
      <Select.Trigger aria-label={ariaLabel || placeholder} className={`app-select-trigger group flex h-11 w-full items-center justify-between gap-3 rounded-xl border border-white/10 bg-slate-900/70 px-3 text-left text-sm text-white shadow-sm backdrop-blur-xl outline-none transition focus:border-emerald-400/50 focus:ring-2 focus:ring-emerald-400/20 disabled:cursor-not-allowed disabled:text-slate-500 ${className}`}>
        <Select.Value placeholder={<span className="text-slate-400">{placeholder}</span>} />
        <Select.Icon asChild><ChevronDown className="app-select-chevron h-4 w-4 shrink-0 text-slate-400 transition-transform duration-[180ms]" aria-hidden="true" /></Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content position="popper" sideOffset={8} collisionPadding={8} className="app-select-content z-[70] max-h-[260px] w-[var(--radix-select-trigger-width)] max-w-[calc(100vw-1rem)] overflow-y-auto rounded-xl border border-white/10 bg-slate-950/95 p-1.5 shadow-[0_16px_40px_rgba(16,185,129,0.2)] backdrop-blur-2xl">
          <Select.Viewport>
            {options.map((option) => (
              <Select.Item key={option.value} value={option.value} disabled={option.disabled} className="relative flex min-h-9 cursor-pointer select-none items-center rounded-lg py-2 pl-8 pr-3 text-sm text-slate-200 outline-none transition data-[highlighted]:bg-emerald-400/15 data-[highlighted]:text-white data-[state=checked]:font-semibold data-[state=checked]:text-emerald-300 data-[disabled]:cursor-not-allowed data-[disabled]:text-slate-500">
                <Select.ItemIndicator className="absolute left-2 grid place-items-center text-emerald-300"><Check size={15} strokeWidth={2.5} /></Select.ItemIndicator>
                <Select.ItemText>{option.label}</Select.ItemText>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  )
}

export default AppSelect

function PageHeader({ title, description, actions }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:mb-8 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-[#F9FAFB]">{title}</h2>
        {description && <p className="mt-1 text-sm text-[#94A3B8]">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-3">{actions}</div>}
    </div>
  )
}

export default PageHeader

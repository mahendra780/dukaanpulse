function Table({ columns = [], data = [], emptyMessage = 'No records found.', getRowKey }) {
  return (
    <div className="overflow-x-auto rounded-3xl border border-white/10 bg-slate-800/50 backdrop-blur-xl transition-all duration-300 hover:border-emerald-400/40 hover:shadow-[0_0_40px_rgba(16,185,129,0.15)]">
      <table className="min-w-full divide-y divide-white/10 text-left text-sm">
        <thead className="bg-white/5">
          <tr>
            {columns.map((column) => (
              <th key={column.key} className="whitespace-nowrap px-5 py-3 font-semibold text-[#94A3B8]">
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {data.length > 0 ? data.map((row, index) => (
            <tr key={getRowKey ? getRowKey(row, index) : row.id || index} className="transition-colors hover:bg-emerald-400/5">
              {columns.map((column) => (
                <td key={column.key} className="whitespace-nowrap px-5 py-3.5 text-slate-200">
                  {column.render ? column.render(row, index) : row[column.key]}
                </td>
              ))}
            </tr>
          )) : (
            <tr>
              <td colSpan={Math.max(columns.length, 1)} className="px-5 py-10 text-center text-[#94A3B8]">
                {emptyMessage}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

export default Table

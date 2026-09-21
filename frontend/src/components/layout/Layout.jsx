import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import { getPageTitle } from './navigation'

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen bg-[#0B1120]">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="min-h-screen lg:pl-80">
        <Navbar title={getPageTitle(pathname)} onMenuClick={() => setSidebarOpen(true)} />
        <main className="h-[calc(100vh-5rem)] overflow-y-auto px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout

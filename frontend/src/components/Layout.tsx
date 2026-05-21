import { Outlet, NavLink } from 'react-router-dom';
import { Shield, Home, FileText, ClipboardCheck } from 'lucide-react';

export default function Layout() {
  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-150 ${
      isActive
        ? 'text-[#533afd] bg-[rgba(83,58,253,0.08)]'
        : 'text-[#64748d] hover:text-[#273951] hover:bg-gray-50'
    }`;

  return (
    <div className="min-h-screen flex flex-col bg-white" style={{ fontFamily: "'Inter', sans-serif" }}>
      {/* Navbar */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-[#e5edf5]">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Left: Logo + Nav */}
          <div className="flex items-center gap-8">
            <NavLink to="/" className="flex items-center gap-2 no-underline">
              <div className="w-8 h-8 rounded-lg bg-[#533afd] flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-semibold text-[#061b31] tracking-tight">
                ContractAI
              </span>
            </NavLink>
            <nav className="flex items-center gap-1">
              <NavLink to="/" className={navLinkClass} end>
                <Home className="w-4 h-4" />
                首页
              </NavLink>
              <NavLink
                to="/"
                className={navLinkClass}
                onClick={() => {
                  setTimeout(() => {
                    document.getElementById('file-list')?.scrollIntoView({ behavior: 'smooth' });
                  }, 100);
                }}
                end
              >
                <FileText className="w-4 h-4" />
                合同列表
              </NavLink>
              <NavLink to="/review/latest" className={navLinkClass}>
                <ClipboardCheck className="w-4 h-4" />
                审查报告
              </NavLink>
            </nav>
          </div>
          {/* Right: Avatar */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#533afd] flex items-center justify-center cursor-pointer">
              <span className="text-white text-sm font-medium">JW</span>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-[#e5edf5] py-6">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <p className="text-sm text-[#64748d]">
            AI智能合同合规审查工具 © 2026
          </p>
        </div>
      </footer>
    </div>
  );
}

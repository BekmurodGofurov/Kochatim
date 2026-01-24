import { LayoutDashboard, Database, ShoppingCart, Settings, Leaf, ChevronRight } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const menu = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Omborxona', path: '/inventory', icon: Database },
  { name: 'Sotuvlar', path: '/sales', icon: ShoppingCart },
  { name: 'Sozlamalar', path: '/settings', icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <div className="hidden md:flex flex-col w-72 bg-white border-r border-slate-100 h-screen sticky top-0 p-8">
      <div className="flex items-center gap-3 mb-12 px-2">
        <div className="bg-green-600 p-2.5 rounded-2xl shadow-lg shadow-green-200 rotate-3">
          <Leaf className="text-white" size={24} />
        </div>
        <span className="text-2xl font-black tracking-tighter text-slate-800">Ko'chatim</span>
      </div>

      <nav className="space-y-3 flex-1">
        {menu.map((item) => {
          const active = location.pathname === item.path;
          return (
            <Link key={item.path} to={item.path} className={`group flex items-center justify-between p-4 rounded-3xl transition-all duration-300 ${
              active ? 'bg-slate-900 text-white shadow-2xl shadow-slate-300 scale-[1.02]' : 'text-slate-500 hover:bg-green-50 hover:text-green-600'
            }`}>
              <div className="flex items-center gap-4">
                <item.icon size={22} className={`${active ? 'text-green-400' : 'group-hover:scale-110 transition-transform'}`} />
                <span className="font-bold tracking-tight">{item.name}</span>
              </div>
              {active && <ChevronRight size={18} className="text-green-400" />}
            </Link>
          );
        })}
      </nav>
      
      <div className="mt-auto p-4 bg-slate-50 rounded-3xl border border-dashed border-slate-200 text-center">
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Premium Plan</p>
        <p className="text-[10px] text-slate-500 mt-1 italic">V1.2.2 build</p>
      </div>
    </div>
  );
}
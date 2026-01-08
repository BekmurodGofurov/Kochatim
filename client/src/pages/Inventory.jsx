import { Plus, Search, Filter, ArrowUpRight } from 'lucide-react';
import { initialSeedlings } from '../data/mockData';

export default function Inventory() {
  return (
    <div className="p-8 lg:p-12 max-w-[1400px] mx-auto">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div>
          <div className="inline-block px-3 py-1 bg-green-100 text-green-700 rounded-full text-[10px] font-black uppercase tracking-widest mb-3">Zaxira Nazorati</div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">Omborxona</h1>
        </div>
        <button className="bg-green-600 text-white px-8 py-4 rounded-[2rem] font-black flex items-center gap-3 hover:bg-slate-900 hover:shadow-2xl hover:shadow-slate-300 transition-all active:scale-95">
          <Plus size={22} /> YANGI NAV QO'SHISH
        </button>
      </header>

      <div className="flex gap-4 mb-10">
        <div className="flex-1 glass-card px-6 py-1 rounded-[2rem] flex items-center gap-4 border-none shadow-sm">
          <Search className="text-slate-400" size={20} />
          <input type="text" placeholder="Nav nomi yoki ID bo'yicha qidirish..." className="bg-transparent w-full py-4 outline-none text-slate-700 font-bold placeholder:font-medium placeholder:text-slate-300" />
        </div>
        <button className="glass-card p-4 rounded-3xl border-none shadow-sm text-slate-600 hover:text-green-600">
          <Filter size={24} />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
        {initialSeedlings.map((s) => (
          <div key={s.id} className="glass-card p-8 rounded-[2.5rem] bg-white group overflow-hidden relative">
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-green-50 rounded-full group-hover:scale-150 transition-transform duration-700 opacity-50" />
            
            <div className="relative">
              <div className="flex justify-between items-start mb-8">
                <div className="bg-slate-900 p-3 rounded-2xl shadow-xl">
                  <ArrowUpRight className="text-green-400" size={20} />
                </div>
                <span className="font-black text-slate-200 text-2xl">#0{s.id}</span>
              </div>
              
              <h3 className="text-2xl font-black text-slate-800 mb-1 group-hover:text-green-700 transition-colors">{s.name}</h3>
              <p className="text-sm font-bold text-slate-400 mb-8 uppercase tracking-tighter">{s.category}</p>

              <div className="space-y-4">
                {[
                  { label: 'Sifat 1', val: s.q1, color: 'text-green-600', bg: 'bg-green-50' },
                  { label: 'Sifat 2', val: s.q2, color: 'text-orange-500', bg: 'bg-orange-50' },
                  { label: 'Sifat 3', val: s.q3, color: 'text-slate-400', bg: 'bg-slate-50' }
                ].map((stat, i) => (
                  <div key={i} className={`flex items-center justify-between p-3 rounded-2xl ${stat.bg} transition-transform group-hover:scale-[1.02]`}>
                    <span className="text-[10px] font-black text-slate-400 uppercase">{stat.label}</span>
                    <span className={`text-lg font-black ${stat.color}`}>{stat.val} dona</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
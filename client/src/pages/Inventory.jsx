import React, { useState } from 'react';
import { Plus, Search, Filter, ArrowLeft, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { DASHBOARD_DATA } from '../data/mockData';

export default function Inventory() {
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [selectedSort, setSelectedSort] = useState(null);
  const [currentImgIndex, setCurrentImgIndex] = useState(0);

  // Rasmni almashtirish funksiyasi
  const nextImg = (imgs) => setCurrentImgIndex((prev) => (prev === imgs.length - 1 ? 0 : prev + 1));
  const prevImg = (imgs) => setCurrentImgIndex((prev) => (prev === 0 ? imgs.length - 1 : prev - 1));

  // 1. GURUHLAR RO'YXATI
  if (!selectedGroup) {
    return (
      <div className="p-8 lg:p-12 max-w-[1400px] mx-auto animate-in fade-in duration-500">
        {/* HEADER - RASMDAGI HOLATDA QOLDI */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div>
            <div className="inline-block px-3 py-1 bg-green-100 text-green-700 rounded-full text-[10px] font-black uppercase tracking-widest mb-3 italic">Zaxira Nazorati</div>
            <h1 className="text-5xl font-black text-slate-900 tracking-tighter">Omborxona</h1>
          </div>
          <button className="bg-[#43a047] text-white px-8 py-4 rounded-2xl font-black flex items-center gap-3 hover:shadow-xl hover:bg-green-700 transition-all active:scale-95 uppercase text-sm">
            <Plus size={20} strokeWidth={3} /> Yangi nav qo'shish
          </button>
        </header>

        <div className="flex items-center gap-2 mb-8">
            <h2 className="text-xl font-black text-slate-400 uppercase tracking-widest italic">Guruhlar</h2>
            <div className="h-[2px] flex-1 bg-slate-100"></div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-10">
          {DASHBOARD_DATA.map((group) => (
            <div key={group.id} onClick={() => setSelectedGroup(group)} 
                 className="group bg-white rounded-[35px] overflow-hidden shadow-sm hover:shadow-2xl hover:-translate-y-3 transition-all duration-500 cursor-pointer">
              <div className="h-64 overflow-hidden">
                <img src={group.mainImage || "https://images.unsplash.com/photo-1560806887-1e4cd0b6bcd6?w=600"} 
                     alt={group.groupName} 
                     className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
              </div>
              <div className="p-8 text-center bg-white">
                <h2 className="text-3xl font-black text-slate-800 uppercase italic tracking-tighter">{group.groupName}</h2>
                <p className="text-xl font-bold text-red-500 mt-2">{group.totalValue.toLocaleString()} dona</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 2. SORTLAR RO'YXATI
  return (
    <div className="p-8 lg:p-12 max-w-[1400px] mx-auto animate-in slide-in-from-right duration-500">
      <button onClick={() => setSelectedGroup(null)} className="mb-10 flex items-center gap-3 font-black text-slate-400 hover:text-green-600 transition-colors uppercase text-xs tracking-widest">
        <ArrowLeft size={18} strokeWidth={3} /> Guruhlarga qaytish
      </button>

      <div className="mb-12">
          <h2 className="text-4xl font-black text-slate-900 uppercase italic">{selectedGroup.groupName} <span className="text-green-600">Navlari</span></h2>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
        {selectedGroup.sorts.map((sort) => (
          <div key={sort.id} onClick={() => { setSelectedSort(sort); setCurrentImgIndex(0); }} 
               className="group bg-white rounded-[30px] overflow-hidden shadow-sm hover:shadow-2xl hover:-translate-y-3 transition-all duration-500 cursor-pointer border border-slate-50">
            <div className="h-48 overflow-hidden bg-slate-100">
              <img src={sort.images?.[0] || "https://images.unsplash.com/photo-1560806887-1e4cd0b6bcd6?w=400"} 
                   alt={sort.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
            </div>
            <div className="p-6">
              <h3 className="font-black text-slate-800 uppercase text-lg mb-4 truncate">{sort.name}</h3>
              {/* NAVLAR TEPAMA-PAST HOLATDA */}
              <div className="space-y-2">
                <div className="flex justify-between items-center bg-slate-50 p-2 px-4 rounded-xl">
                    <span className="text-[10px] font-black text-slate-400 uppercase">1-Nav</span>
                    <span className="font-black text-green-600">{sort.nav1}</span>
                </div>
                <div className="flex justify-between items-center bg-slate-50 p-2 px-4 rounded-xl">
                    <span className="text-[10px] font-black text-slate-400 uppercase">2-Nav</span>
                    <span className="font-black text-orange-500">{sort.nav2}</span>
                </div>
                <div className="flex justify-between items-center bg-slate-50 p-2 px-4 rounded-xl">
                    <span className="text-[10px] font-black text-slate-400 uppercase">3-Nav</span>
                    <span className="font-black text-slate-500">{sort.nav3}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* DETALLAR MODALI (SLIDER BILAN) */}
      {selectedSort && (
        <div className="fixed inset-0 bg-slate-900/90 backdrop-blur-md z-50 flex items-center justify-center p-6">
          <div className="bg-white w-full max-w-6xl h-[85vh] rounded-[45px] overflow-hidden flex flex-col md:flex-row shadow-2xl animate-in zoom-in duration-300">
            
            {/* CHAP TOMON: RASM SLIDER */}
            <div className="w-full md:w-[60%] h-full bg-black relative group/slider">
              <img src={selectedSort.images[currentImgIndex]} 
                   className="w-full h-full object-contain" alt="Sort" />
              
              {/* Slider tugmalari */}
              {selectedSort.images.length > 1 && (
                <>
                  <button onClick={(e) => { e.stopPropagation(); prevImg(selectedSort.images); }} 
                          className="absolute left-6 top-1/2 -translate-y-1/2 p-4 bg-white/10 hover:bg-white text-white hover:text-black rounded-full backdrop-blur-md transition-all">
                    <ChevronLeft size={30} />
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); nextImg(selectedSort.images); }} 
                          className="absolute right-6 top-1/2 -translate-y-1/2 p-4 bg-white/10 hover:bg-white text-white hover:text-black rounded-full backdrop-blur-md transition-all">
                    <ChevronRight size={30} />
                  </button>
                  {/* Nuqtalar */}
                  <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex gap-2">
                    {selectedSort.images.map((_, i) => (
                      <div key={i} className={`h-2 rounded-full transition-all ${i === currentImgIndex ? 'w-8 bg-white' : 'w-2 bg-white/40'}`}></div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* O'NG TOMON: MA'LUMOTLAR */}
            <div className="w-full md:w-[40%] p-12 overflow-y-auto flex flex-col bg-white">
              <div className="flex justify-between items-start mb-6">
                <h2 className="text-4xl font-black text-slate-900 uppercase italic tracking-tighter leading-none">{selectedSort.name}</h2>
                <button onClick={() => setSelectedSort(null)} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
                  <X size={28} />
                </button>
              </div>
              
              <div className="h-1.5 w-20 bg-green-500 rounded-full mb-10"></div>
              
              <div className="space-y-4 mb-10">
                 <h4 className="text-xs font-black text-slate-400 uppercase tracking-[0.2em]">Sifat bo'yicha zaxira</h4>
                 <div className="grid grid-cols-1 gap-3">
                    <div className="p-4 bg-green-50 rounded-2xl flex justify-between items-center border border-green-100">
                        <span className="font-black text-green-700">1-NAV</span>
                        <span className="text-2xl font-black text-green-800">{selectedSort.nav1} ta</span>
                    </div>
                    <div className="p-4 bg-orange-50 rounded-2xl flex justify-between items-center border border-orange-100">
                        <span className="font-black text-orange-600">2-NAV</span>
                        <span className="text-2xl font-black text-orange-700">{selectedSort.nav2} ta</span>
                    </div>
                    <div className="p-4 bg-slate-50 rounded-2xl flex justify-between items-center border border-slate-200">
                        <span className="font-black text-slate-500">3-NAV</span>
                        <span className="text-2xl font-black text-slate-800">{selectedSort.nav3} ta</span>
                    </div>
                 </div>
              </div>

              <div className="flex-1">
                <h4 className="text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-4">Nav haqida ma'lumot</h4>
                <p className="text-lg font-bold text-slate-600 leading-relaxed italic">
                  {selectedSort.description || "Ushbu nav haqida qo'shimcha ma'lumot mavjud emas."}
                </p>
              </div>

              <div className="mt-12 pt-8 border-t border-slate-100 flex justify-between items-center">
                <div>
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Umumiy soni</p>
                  <p className="text-4xl font-black text-slate-900">{selectedSort.nav1 + selectedSort.nav2 + selectedSort.nav3}</p>
                </div>
                <button className="bg-slate-900 text-white px-8 py-4 rounded-2xl font-black hover:bg-green-600 transition-all uppercase text-xs tracking-widest">
                  Tahrirlash
                </button>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
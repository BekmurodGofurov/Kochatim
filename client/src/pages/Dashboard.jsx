import React, { useState, useRef } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { LayoutDashboard, Loader2 } from 'lucide-react';
import { DASHBOARD_DATA } from '../data/mockData';

const Dashboard = () => {
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [loading, setLoading] = useState(false);
  const detailsRef = useRef(null);

  const COLORS = ['#3b82f6', '#fbbf24', '#c084fc', '#f87171', '#34d399'];

  const handleGroupClick = (group) => {
    setLoading(true);
    setSelectedGroup(null);
    
    setTimeout(() => {
      setSelectedGroup(group);
      setLoading(false);
      if (detailsRef.current) {
        detailsRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }, 400);
  };

  const mainPieData = DASHBOARD_DATA.map((item, index) => ({
    name: item.groupName,
    value: item.totalValue,
    color: COLORS[index % COLORS.length],
    original: item
  }));

  return (
    <div className="p-6 space-y-8 bg-[#F8FAFC] min-h-screen pb-20">
      
      {/* 1. ASOSIY QISM */}
      <div className="bg-white p-10 rounded-[30px] shadow-md border border-gray-100 flex flex-col lg:flex-row items-center gap-10">
        <div className="w-full lg:w-1/2 space-y-4 order-2 lg:order-1">
          <h2 className="text-2xl font-black text-gray-800 uppercase mb-6 flex items-center gap-2">
            <LayoutDashboard className="text-blue-500" /> Guruhlar hisoboti
          </h2>
          {mainPieData.map((item, index) => (
            <div 
              key={index} 
              onClick={() => handleGroupClick(item.original)}
              className={`flex justify-between items-center p-5 rounded-2xl cursor-pointer transition-all border ${
                selectedGroup?.id === item.original.id ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-transparent hover:bg-gray-100'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: item.color }}></div>
                <span className="font-bold text-gray-700">{item.name}</span>
              </div>
              <span className="font-black text-lg">{item.value.toLocaleString()} dona</span>
            </div>
          ))}
        </div>

        <div className="w-full lg:w-1/2 h-[400px] order-1 lg:order-2">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={mainPieData}
                cx="50%"
                cy="50%"
                outerRadius={160}
                dataKey="value"
                stroke="#fff"
                strokeWidth={4}
              >
                {mainPieData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.color} 
                    onClick={() => handleGroupClick(entry.original)}
                    className="outline-none cursor-pointer"
                  />
                ))}
              </Pie>
              {/* Asosiy Pie Tooltip: Masalan "Olma: 45%" */}
              <Tooltip 
                formatter={(value, name) => [
                  `${((value / mainPieData.reduce((a, b) => a + b.value, 0)) * 100).toFixed(1)}%`, 
                  name
                ]} 
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. BATAHSIL MA'LUMOT BO'LIMI */}
      <div ref={detailsRef} className="min-h-[450px] scroll-mt-10">
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 text-blue-500">
            <Loader2 className="animate-spin mb-4" size={48} />
            <p className="font-bold uppercase tracking-widest text-xs">Yuklanmoqda...</p>
          </div>
        )}

        {selectedGroup && !loading && (
          <div className="bg-white p-10 rounded-[30px] shadow-md border border-gray-100 animate-in fade-in zoom-in duration-300">
            <div className="flex flex-col lg:flex-row gap-12">
              
              {/* Chap: Sortlar va Navlar */}
              <div className="flex-1 space-y-6">
                <h3 className="text-3xl font-black text-gray-800 border-b pb-4">
                  {selectedGroup.groupName} <span className="text-gray-400 font-light">/ Sortlar soni</span>
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {selectedGroup.sorts.map((sort, idx) => (
                    <div key={idx} className="bg-gray-50 p-6 rounded-[25px] border border-gray-100">
                      {/* Sort nomi kattalashtirildi */}
                      <p className="text-lg font-black uppercase tracking-tight mb-1" style={{ color: COLORS[idx % COLORS.length] }}>
                        {sort.name}
                      </p>
                      {/* Jami soni biroz kichraytirildi */}
                      <div className="text-2xl font-bold text-gray-700 mb-4">
                        {(sort.nav1 + sort.nav2 + sort.nav3).toLocaleString()} <span className="text-xs font-normal text-gray-400">dona jami</span>
                      </div>
                      <div className="flex justify-between border-t pt-4 text-center">
                        <div><p className="text-[10px] text-gray-400 font-bold uppercase">1-Nav</p><p className="font-bold">{sort.nav1}</p></div>
                        <div><p className="text-[10px] text-gray-400 font-bold uppercase">2-Nav</p><p className="font-bold text-gray-500">{sort.nav2}</p></div>
                        <div><p className="text-[10px] text-gray-400 font-bold uppercase">3-Nav</p><p className="font-bold text-gray-400">{sort.nav3}</p></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* O'ng: Sortlar Pie Chart */}
              <div className="w-full lg:w-80 flex flex-col items-center justify-center bg-gray-50 rounded-[30px] p-8 h-fit">
                <h4 className="text-[10px] font-black text-gray-400 uppercase mb-4 tracking-widest text-center leading-tight">
                  {selectedGroup.groupName} bo'yicha ulush (%)
                </h4>
                <div className="h-60 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={selectedGroup.sorts.map(s => ({ name: s.name, value: s.nav1 + s.nav2 + s.nav3 }))}
                        outerRadius={80}
                        stroke="#fff"
                        strokeWidth={2}
                        dataKey="value"
                      >
                        {selectedGroup.sorts.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      {/* Tooltip: Endi "Golden: 40.5%" ko'rinishida chiqadi */}
                      <Tooltip 
                        formatter={(value, name) => [
                          `${((value / selectedGroup.totalValue) * 100).toFixed(1)}%`, 
                          name
                        ]} 
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-4 text-3xl font-black text-gray-800">{selectedGroup.totalValue.toLocaleString()}</p>
                <p className="text-[10px] text-gray-400 font-black uppercase tracking-widest text-center">Jami {selectedGroup.groupName}</p>
              </div>

            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
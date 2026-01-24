import React, { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { History, TrendingUp, Calendar, Wallet } from 'lucide-react';
// Ma'lumotlarni import qilamiz
import { SALES_HISTORY, MONTHLY_PIE_DATA } from '../../data/mockData';

const Sales = () => {
  const [visibleCount, setVisibleCount] = useState(10);

  const loadMore = () => {
    setVisibleCount(prev => prev + 10);
  };

  // Jami tushumni hisoblash
  const totalRevenue = MONTHLY_PIE_DATA.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-8 bg-[#F8FAFC] min-h-screen">
      
      {/* CHAP TOMON: Sotuvlar tarixi */}
      <div className="bg-white p-8 rounded-[35px] shadow-sm border border-gray-100">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 bg-green-50 rounded-2xl text-green-600">
            <History size={24} />
          </div>
          <h2 className="text-2xl font-black text-gray-800 tracking-tight">Sotuvlar tarixi</h2>
        </div>

        <div className="space-y-4">
          {SALES_HISTORY.slice(0, visibleCount).map((item) => (
            <div key={item.id} className="flex justify-between items-center p-5 bg-gray-50 rounded-[22px] hover:bg-white hover:shadow-md transition-all duration-300 border border-transparent hover:border-gray-100 group">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center text-gray-400 group-hover:text-green-500 transition">
                  <Wallet size={20} />
                </div>
                <div>
                  <h4 className="font-bold text-gray-800 text-lg">{item.name}</h4>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-[10px] bg-green-100 px-2 py-0.5 rounded-lg text-green-700 font-black uppercase">
                      {item.category}
                    </span>
                    <p className="text-xs text-gray-400 flex items-center gap-1 font-medium">
                      <Calendar size={12} /> {item.date} • {item.qty} dona
                    </p>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="font-black text-green-600 text-lg">+{item.price.toLocaleString()} so'm</p>
              </div>
            </div>
          ))}
        </div>

        {visibleCount < SALES_HISTORY.length && (
          <button 
            onClick={loadMore}
            className="w-full mt-8 py-4 border-2 border-dashed border-gray-200 text-gray-400 rounded-2xl hover:border-green-500 hover:text-green-600 transition-all font-bold uppercase tracking-widest text-xs"
          >
            Yana yuklash (+10)
          </button>
        )}
      </div>

      {/* O'NG TOMON: Analytics Pie Chart */}
      <div className="bg-white p-8 rounded-[35px] shadow-sm border border-gray-100 h-fit sticky top-6">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-50 rounded-2xl text-blue-600">
              <TrendingUp size={24} />
            </div>
            <div>
              <h2 className="text-2xl font-black text-gray-800 tracking-tight">Daromad tahlili</h2>
              <p className="text-xs text-gray-400 font-bold uppercase tracking-widest">Oylik hisobot (%)</p>
            </div>
          </div>
        </div>

        {/* Pie Chart qismi */}
        <div className="relative h-[350px] w-full bg-gray-50 rounded-[30px] p-4">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={MONTHLY_PIE_DATA}
                innerRadius={90}
                outerRadius={130}
                paddingAngle={8}
                dataKey="value"
                stroke="none"
              >
                {MONTHLY_PIE_DATA.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} className="outline-none" />
                ))}
              </Pie>
              {/* Pie chartda foiz ko'rsatish */}
              <Tooltip 
                formatter={(value) => [`${((value / totalRevenue) * 100).toFixed(1)}%`, "Ulushi"]}
                contentStyle={{ borderRadius: '15px', border: 'none', boxShadow: '0 10px 15px rgba(0,0,0,0.1)' }}
              />
            </PieChart>
          </ResponsiveContainer>
          
          {/* Pie Chart o'rtasidagi Jami summa */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <p className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-1">Jami tushum</p>
            <p className="text-3xl font-black text-gray-800">{totalRevenue.toLocaleString()}</p>
            <p className="text-xs font-bold text-green-500 mt-1">so'm</p>
          </div>
        </div>

        {/* Pastdagi ro'yxat: Endi faqat SUMMAda */}
        <div className="mt-10 space-y-5">
          <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-4">Guruhlar bo'yicha tushum:</h3>
          {MONTHLY_PIE_DATA.map((item, i) => (
            <div key={i} className="group">
              <div className="flex justify-between items-end mb-2">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full shadow-sm" style={{ backgroundColor: item.color }}></div>
                  <span className="text-gray-700 font-bold text-lg">{item.name}</span>
                </div>
                {/* Bu yerda foiz emas, SUMMA ko'rsatiladi */}
                <span className="font-black text-gray-800">{item.value.toLocaleString()} so'm</span>
              </div>
              <div className="w-full bg-gray-100 h-2 rounded-full overflow-hidden shadow-inner">
                <div 
                  className="h-full rounded-full transition-all duration-1000 group-hover:opacity-80" 
                  style={{ 
                    width: `${(item.value / totalRevenue) * 100}%`, 
                    backgroundColor: item.color 
                  }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
};

export default Sales;
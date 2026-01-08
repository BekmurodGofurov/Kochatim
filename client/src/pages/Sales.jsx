import React, { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { History, TrendingUp, Calendar } from 'lucide-react';
// Ma'lumotlarni import qilamiz
import { SALES_HISTORY, MONTHLY_PIE_DATA } from '../data/mockData';

const Sales = () => {
  const [visibleCount, setVisibleCount] = useState(10);

  const loadMore = () => {
    setVisibleCount(prev => prev + 10);
  };

  const totalRevenue = MONTHLY_PIE_DATA.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
      
      {/* CHAP TOMON: Sotuvlar tarixi */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 mb-6">
          <History className="text-green-600" size={24} />
          <h2 className="text-xl font-bold text-gray-800">Sotuvlar tarixi</h2>
        </div>

        <div className="space-y-3">
          {SALES_HISTORY.slice(0, visibleCount).map((item) => (
            <div key={item.id} className="flex justify-between items-center p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition">
              <div>
                <h4 className="font-semibold text-gray-800">{item.name}</h4>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-[10px] bg-white px-2 py-0.5 rounded border text-gray-400 font-medium">
                    {item.category}
                  </span>
                  <p className="text-xs text-gray-500 flex items-center gap-1">
                    <Calendar size={12} /> {item.date} • {item.qty} dona
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="font-bold text-green-600">+{item.price.toLocaleString()} so'm</p>
              </div>
            </div>
          ))}
        </div>

        {visibleCount < SALES_HISTORY.length && (
          <button 
            onClick={loadMore}
            className="w-full mt-6 py-3 border-2 border-dashed border-gray-200 text-gray-500 rounded-xl hover:border-green-500 hover:text-green-600 transition font-medium"
          >
            Ko'proq ko'rsatish (+10)
          </button>
        )}
      </div>

      {/* O'NG TOMON: Analytics Pie Chart */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 h-fit sticky top-6">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="text-blue-600" size={24} />
          <h2 className="text-xl font-bold text-gray-800">Daromad ulushi (%)</h2>
        </div>
        <p className="text-sm text-gray-500 mb-6">Oxirgi bir oylik tushumlar tahlili</p>

        <div className="h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={MONTHLY_PIE_DATA}
                innerRadius={85}
                outerRadius={120}
                paddingAngle={5}
                dataKey="value"
              >
                {MONTHLY_PIE_DATA.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip formatter={(value) => `${value.toLocaleString()} so'm`} />
              <Legend verticalAlign="bottom" height={36}/>
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-8 space-y-4">
          {MONTHLY_PIE_DATA.map((item, i) => (
            <div key={i}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-600 font-medium">{item.name}</span>
                <span className="font-bold">{((item.value / totalRevenue) * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-100 h-1.5 rounded-full">
                <div 
                  className="h-full rounded-full" 
                  style={{ width: `${(item.value / totalRevenue) * 100}%`, backgroundColor: item.color }}
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
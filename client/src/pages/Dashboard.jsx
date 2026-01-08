import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Sprout, TrendingUp, AlertTriangle, DollarSign } from 'lucide-react';

// Mock Data - Ombor holati
const data = [
  { name: 'Olma', value: 450, color: '#10b981' },
  { name: 'Gilos', value: 300, color: '#ef4444' },
  { name: 'Yong‘oq', value: 200, color: '#f59e0b' },
  { name: 'Archa', value: 150, color: '#3b82f6' },
  { name: 'Atirgul', value: 100, color: '#ec4899' },
];

const stats = [
  { title: 'Jami ko‘chatlar', value: '1,200', icon: Sprout, color: 'text-green-600' },
  { title: 'Bugungi sotuv', value: '4.5 mln', icon: TrendingUp, color: 'text-blue-600' },
  { title: 'Kam qolgan', value: '3 tur', icon: AlertTriangle, color: 'text-red-600' },
  { title: 'Oylik foyda', value: '28 mln', icon: DollarSign, color: 'text-purple-600' },
];

const Dashboard = () => {
  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Statistika kartochkalari */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {stats.map((item, index) => (
          <div key={index} className="bg-white p-4 rounded-xl shadow-sm flex items-center gap-4">
            <div className={`p-3 rounded-lg bg-gray-100 ${item.color}`}>
              <item.icon size={24} />
            </div>
            <div>
              <p className="text-sm text-gray-500">{item.title}</p>
              <p className="text-xl font-bold">{item.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Grafik qismi */}
      <div className="bg-white p-6 rounded-xl shadow-sm">
        <h2 className="text-lg font-semibold mb-4">Ombor tarkibi (Turiga ko‘ra)</h2>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
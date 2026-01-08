import React from 'react';
import { User, Shield, Bot, Smartphone, LogOut, Info } from 'lucide-react';
import { USER_PROFILE, BOT_SETTINGS } from '../data/mockData';

const Settings = () => {
  return (
    <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      {/* CHAP TOMON: Profil ma'lumotlari */}
      <div className="lg:col-span-2 space-y-6">
        
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center text-green-600">
              <User size={40} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-800">{USER_PROFILE.name}</h2>
              <p className="text-gray-500 font-medium">{USER_PROFILE.role}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Inputlar "readOnly" va fon rangi biroz kulrang qilingan */}
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Telefon raqam</label>
              <div className="w-full p-3 rounded-xl border border-gray-100 bg-gray-50 text-gray-600">
                {USER_PROFILE.phone}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Manzil</label>
              <div className="w-full p-3 rounded-xl border border-gray-100 bg-gray-50 text-gray-600">
                {USER_PROFILE.location}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Ro'yxatdan o'tilgan sana</label>
              <div className="w-full p-3 rounded-xl border border-gray-100 bg-gray-50 text-gray-600">
                {USER_PROFILE.joined}
              </div>
            </div>
          </div>

          <div className="mt-8 p-4 bg-blue-50 rounded-xl flex items-start gap-3 text-blue-700 text-sm">
            <Info size={20} className="shrink-0" />
            <p>Shaxsiy ma'lumotlarni o'zgartirish uchun tizim administratoriga murojaat qiling.</p>
          </div>
        </div>

        {/* Xavfsizlik bo'limi */}
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
            <Shield className="text-blue-500" /> Tizim himoyasi
          </h3>
          <div className="p-4 bg-gray-50 rounded-xl flex justify-between items-center text-sm">
            <span className="text-gray-600">Hisob holati:</span>
            <span className="bg-green-100 text-green-600 px-3 py-1 rounded-full font-bold">Faol</span>
          </div>
        </div>
      </div>

      {/* O'NG TOMON: Telegram Bot ma'lumotlari */}
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 text-sm">
          <div className="flex items-center gap-2 mb-6">
            <Bot className="text-green-500" size={24} />
            <h3 className="text-lg font-bold text-gray-800">Bot Ma'lumotlari</h3>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-gray-400 text-xs mb-1 uppercase">Telegram Bot ID</p>
              <p className="font-mono bg-gray-50 p-2 rounded border border-gray-100">{BOT_SETTINGS.chatId}</p>
            </div>
            
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-xl text-green-700">
              <span className="font-medium">Sotuv xabarnomalari</span>
              <span className="font-bold text-xs">YOQILGAN</span>
            </div>

            <button className="w-full py-3 bg-gray-100 text-gray-500 rounded-xl font-bold flex items-center justify-center gap-2 cursor-not-allowed">
              <Smartphone size={18} /> Botni sozlash (Yopiq)
            </button>
          </div>
        </div>

        <button className="w-full py-4 bg-red-50 text-red-600 rounded-2xl font-bold flex items-center justify-center gap-2 hover:bg-red-600 hover:text-white transition">
          <LogOut size={20} /> Tizimdan chiqish
        </button>
      </div>

    </div>
  );
};

export default Settings;
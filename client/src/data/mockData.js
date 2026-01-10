// src/data/mockData.js

export const DASHBOARD_DATA = [
  {
    id: "olma",
    groupName: "Olma",
    totalValue: 1250,
    mainImage: "https://zamin.uz/uploads/posts/2025-03/640336f4e4_olma-apple-yabloko.webp",
    color: "#ef4444",
    sorts: [
      { 
        id: 101,
        name: "Semerenka", 
        nav1: 350, nav2: 120, nav3: 45,
        images: [
          "https://healthy-food-near-me.com/wp-content/uploads/2022/09/apple-variety-semerenko-characteristic-with-photo-and-video.webp",
          "https://www.buxstat.uz/images/news/olma1.jpg",
          "https://www.ziyouz.uz/wp-content/uploads/2015/07/olma.jpg"
        ],
        description: "Semerenka - qishki nav, mevalari yashil, nordon-shirin. Uzoq masofaga tashishga chidamli va 6 oygacha sifatini yo'qotmaydi."
      },
      { 
        id: 102,
        name: "Golden Delicious", 
        nav1: 280, nav2: 60, nav3: 15,
        images: [
          "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/Golden_Delicious_apples.jpg/2560px-Golden_Delicious_apples.jpg",
          "https://data.daryo.uz/media/2023/04/643ecb7c8989f.jpg"
        ],
        description: "Tilla-sariq rangli, juda shirin va xushbo'y olma. Bolalar uchun eng sevimli nav hisoblanadi."
      },
      { 
        id: 103,
        name: "Pink Lady", 
        nav1: 150, nav2: 30, nav3: 10,
        images: ["https://images.unsplash.com/photo-1584306235453-43214b736706?w=600"],
        description: "Eksport uchun eng ko'p talab qilinadigan premium navlardan biri. Qizg'ish-pushti rangda."
      },
      { 
        id: 104,
        name: "Fuji", 
        nav1: 180, nav2: 10, nav3: 0,
        images: ["https://images.unsplash.com/photo-1590005354167-6da97870c91d?w=600"],
        description: "Yaponiyada yaratilgan, suvli va qattiq olma navi. Shakar miqdori juda yuqori."
      }
    ]
  },
  {
    id: "orik",
    groupName: "O'rik",
    totalValue: 980,
    mainImage: "https://makepedia.uz/wp-content/uploads/2020/01/tushda-orik.jpg",
    color: "#f59e0b",
    sorts: [
      { 
        id: 201,
        name: "Qandak", 
        nav1: 400, nav2: 80, nav3: 20,
        images: [
          "https://images.unsplash.com/photo-1543528176-51368a6e01a0?w=600",
          "https://images.unsplash.com/photo-1501199532022-dc3b16bd3db5?w=600"
        ],
        description: "O'rta Osiyo iqlimiga mos eng shirin o'rik navi. Asosan quritish (turshak) uchun ishlatiladi."
      },
      { 
        id: 202,
        name: "Subhon", 
        nav1: 220, nav2: 40, nav3: 10,
        images: ["https://images.unsplash.com/photo-1629986345991-3893663a879d?w=600"],
        description: "Yirik mevali, sershira nav. Yangiligida iste'mol qilish uchun juda qulay."
      },
      { 
        id: 203,
        name: "Oq O'rik", 
        nav1: 180, nav2: 25, nav3: 5,
        images: ["https://images.unsplash.com/photo-1543528176-51368a6e01a0?w=600"],
        description: "Rangi och-sariq, mazasi o'ziga xos mayin. Konserva sanoatida ko'p foydalaniladi."
      }
    ]
  },
  {
    id: "shaftoli",
    groupName: "Shaftoli",
    totalValue: 740,
    mainImage: "https://img.pikbest.com/wp/202409/peach-fruits-gray-textured-table-adorned-with-luscious-in-a-string-bag_9912549.jpg!w700wp",
    color: "#f43f5e",
    sorts: [
      { 
        id: 301,
        name: "Lola", 
        nav1: 300, nav2: 50, nav3: 10,
        images: [
          "https://images.unsplash.com/photo-1595124253349-20f0e6c7393a?w=600",
          "https://images.unsplash.com/photo-1626014303757-6bcbe77bc88f?w=600"
        ],
        description: "O'rtapishar nav, mevalari yumshoq va mayin tukli. Soki (sharbat) tayyorlash uchun ideal."
      },
      { 
        id: 302,
        name: "Anjir Shaftoli", 
        nav1: 250, nav2: 10, nav3: 0,
        images: ["https://images.unsplash.com/photo-1622340322700-476c59709f6e?w=600"],
        description: "Yassi shaklli, o'ziga xos xushbo'y hidli nav. Hozirgi kunda bozorda eng xaridorgir."
      },
      { 
        id: 303,
        name: "Nektarin", 
        nav1: 100, nav2: 20, nav3: 0,
        images: ["https://images.unsplash.com/photo-1598413159048-5228c2e6f477?w=600"],
        description: "Tuksiz, silliq po'stloqli shaftoli. Qattiqroq bo'lgani uchun uzoq muddat saqlash mumkin."
      }
    ]
  }
];



export const SALES_HISTORY = [
  { id: 1, name: 'Olma (Golden)', price: 250000, qty: 10, date: '2024-05-15', category: 'Mevali' },
  { id: 2, name: 'Gilos (Sariq)', price: 140000, qty: 4, date: '2024-05-15', category: 'Mevali' },
  { id: 3, name: 'Archa (Qrim)', price: 750000, qty: 5, date: '2024-05-14', category: 'Manzarali' },
  { id: 4, name: 'Yong‘oq (Ideal)', price: 450000, qty: 10, date: '2024-05-14', category: 'Mevali' },
  { id: 5, name: 'Atirgul (Qizil)', price: 150000, qty: 10, date: '2024-05-13', category: 'Gullar' },
  { id: 6, name: 'Behi (Shirin)', price: 300000, qty: 12, date: '2024-05-13', category: 'Mevali' },
  { id: 7, name: 'Limon', price: 500000, qty: 2, date: '2024-05-12', category: 'Mevali' },
  { id: 8, name: 'Bodom', price: 900000, qty: 3, date: '2024-05-12', category: 'Mevali' },
  { id: 9, name: 'Uzum (Husayni)', price: 200000, qty: 20, date: '2024-05-11', category: 'Mevali' },
  { id: 10, name: 'Anor', price: 180000, qty: 6, date: '2024-05-11', category: 'Mevali' },
  { id: 11, name: 'Siren (Binafsha)', price: 120000, qty: 3, date: '2024-05-10', category: 'Gullar' },
  { id: 12, name: 'Oqqayin', price: 600000, qty: 4, date: '2024-05-10', category: 'Manzarali' },
  { id: 13, name: 'Shaftoli', price: 220000, qty: 15, date: '2024-05-09', category: 'Mevali' },
  { id: 14, name: 'Kashtan', price: 850000, qty: 2, date: '2024-05-09', category: 'Manzarali' },
  { id: 15, name: 'Lola', price: 50000, qty: 50, date: '2024-05-08', category: 'Gullar' },
  { id: 16, name: 'Nok (Muz)', price: 280000, qty: 7, date: '2024-05-08', category: 'Mevali' },
  { id: 17, name: 'Sharq chinori', price: 1200000, qty: 1, date: '2024-05-07', category: 'Manzarali' },
  { id: 18, name: 'Malina', price: 100000, qty: 25, date: '2024-05-07', category: 'Butalar' },
  { id: 19, name: 'Smorodina', price: 90000, qty: 15, date: '2024-05-06', category: 'Butalar' },
  { id: 20, name: 'Nilufar', price: 45000, qty: 30, date: '2024-05-06', category: 'Gullar' },
  { id: 21, name: 'Xurmo', price: 320000, qty: 5, date: '2024-05-05', category: 'Mevali' },
  { id: 22, name: 'Sliva', price: 150000, qty: 8, date: '2024-05-05', category: 'Mevali' },
  { id: 23, name: 'Magnoliya', price: 1500000, qty: 1, date: '2024-05-04', category: 'Manzarali' },
  { id: 24, name: 'Gortenziya', price: 300000, qty: 4, date: '2024-05-04', category: 'Gullar' },
  { id: 25, name: "O'rik", price: 200000, qty: 12, date: '2024-05-03', category: 'Mevali' },
  { id: 26, name: 'Tut (Buxoro)', price: 180000, qty: 10, date: '2024-05-03', category: 'Mevali' },
  { id: 27, name: 'Samshat', price: 40000, qty: 100, date: '2024-05-02', category: 'Butalar' },
  { id: 28, name: 'Mojjevelnik', price: 250000, qty: 6, date: '2024-05-02', category: 'Manzarali' },
  { id: 29, name: 'Gilos (Qora)', price: 380000, qty: 5, date: '2024-05-01', category: 'Mevali' },
  { id: 30, name: 'Atirgul (Oq)', price: 150000, qty: 10, date: '2024-05-01', category: 'Gullar' },
];
// src/data/mockData.js fayliga qo'shing:

export const initialSeedlings = [
  { id: 1, name: 'Olma (Golden)', category: 'Mevali', price: 25000, stock: 45, age: '2 yillik', health: 'A' },
  { id: 2, name: 'Gilos (Sariq)', category: 'Mevali', price: 35000, stock: 12, age: '3 yillik', health: 'A+' },
  { id: 3, name: 'Yong‘oq (Ideal)', category: 'Mevali', price: 45000, stock: 28, age: '1 yillik', health: 'B' },
  { id: 4, name: 'Archa (Qrim)', category: 'Manzarali', price: 150000, stock: 8, age: '4 yillik', health: 'A' },
  { id: 5, name: 'Atirgul (Qizil)', category: 'Gullar', price: 15000, stock: 120, age: '1 yillik', health: 'A' },
  { id: 6, name: 'Limon (Meyera)', category: 'Mevali', price: 55000, stock: 15, age: '2 yillik', health: 'A+' },
  { id: 7, name: 'Oqqayin', category: 'Manzarali', price: 85000, stock: 20, age: '3 yillik', health: 'B+' },
  { id: 8, name: 'Behi (Samarqand)', category: 'Mevali', price: 30000, stock: 35, age: '2 yillik', health: 'A' },
  { id: 9, name: 'Shaftoli (Lola)', category: 'Mevali', price: 28000, stock: 50, age: '1 yillik', health: 'A' },
  { id: 10, name: 'Kashtan', category: 'Manzarali', price: 200000, stock: 5, age: '5 yillik', health: 'A+' },
];

export const MONTHLY_PIE_DATA = [
  { name: 'Mevali', value: 5800000, color: '#10b981' },
  { name: 'Manzarali', value: 4100000, color: '#3b82f6' },
  { name: 'Gullar', value: 1500000, color: '#ec4899' },
  { name: 'Butalar', value: 950000, color: '#f59e0b' },
];

// src/data/mockData.js ga pastdagilarni qo'shing
export const USER_PROFILE = {
  name: "Bekmurod G‘ofurov",
  role: "Admin / Egasi",
  phone: "+998 33 666 08 18",
  location: "Andijon, O‘zbekiston",
  joined: "Yanvar, 2023"
};

export const BOT_SETTINGS = {
  botToken: "7483...839",
  chatId: "59382011341",
  dailyReports: true,
  saleAlerts: true
};
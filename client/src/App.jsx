import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebarr from './components/Sidebar.jsx'
import Inventory from './pages/Inventory.jsx';

function App() {
  return (
    <Router>
      <div className="flex min-h-screen bg-[#F8FAFC]">
        <Sidebarr />
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<div className="p-20 text-center opacity-20 font-black text-5xl">DASHBOARD</div>} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/sales" element={<div className="p-20 text-center opacity-20 font-black text-5xl">SOTUVLAR</div>} />
            <Route path="/settings" element={<div className="p-20 text-center opacity-20 font-black text-5xl">SOZLAMALAR</div>} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebarr from './components/Sidebar.jsx'
import Inventory from './pages/Inventory.jsx';
import Dashboard from './pages/Dashboard.jsx'; // Dashboardni import qilamiz
import Sales from './pages/Sales.jsx';
import Settings from './pages/Settings.jsx';

function App() {
  return (
    <Router>
      <div className="flex min-h-screen bg-[#F8FAFC]">
        <Sidebarr />
        <div className="flex-1">
          <Routes>
            {/* Endi bu yerda oddiy matn emas, biz yaratgan Dashboard komponenti chiqadi */}
            <Route path="/" element={<Dashboard />} />
            
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/sales" element={<Sales />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
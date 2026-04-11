import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Landing from './pages/Landing';
import Analyze from './pages/Analyze';
import Corpus from './pages/Corpus';

export default function App() {
  return (
    <BrowserRouter>
      <div className="noise">
        <Navbar />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/analyze" element={<Analyze />} />
          <Route path="/corpus" element={<Corpus />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

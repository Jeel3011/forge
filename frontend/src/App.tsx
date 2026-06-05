import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Noise } from "./components/Noise";
import { Nav } from "./components/Nav";
import Landing from "./pages/Landing";
import Home from "./pages/Home";
import Diagnose from "./pages/Diagnose";
import Questionnaire from "./pages/Questionnaire";
import Output from "./pages/Output";

export default function App() {
  return (
    <BrowserRouter>
      <Noise />
      <Routes>
        {/* Landing page has its own Nav embedded */}
        <Route path="/" element={<><Nav /><Landing /></>} />

        {/* App flow — no Nav (has its own top bar) */}
        <Route path="/app" element={<Home />} />
        <Route path="/diagnose" element={<Diagnose />} />
        <Route path="/questionnaire" element={<Questionnaire />} />
        <Route path="/output" element={<Output />} />
      </Routes>
    </BrowserRouter>
  );
}

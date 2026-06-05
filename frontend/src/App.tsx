import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Diagnose from "./pages/Diagnose";
import Questionnaire from "./pages/Questionnaire";
import Output from "./pages/Output";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/diagnose" element={<Diagnose />} />
        <Route path="/questionnaire" element={<Questionnaire />} />
        <Route path="/output" element={<Output />} />
      </Routes>
    </BrowserRouter>
  );
}

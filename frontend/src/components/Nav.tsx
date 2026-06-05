import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

export function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const { pathname } = useLocation();
  const isLanding = pathname === "/";

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-40 transition-all duration-500 ${
        scrolled || !isLanding
          ? "bg-forge-bg/90 backdrop-blur-xl border-b border-forge-border"
          : "bg-transparent"
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-lg bg-forge-white flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 12L7 2L12 12" stroke="#080808" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M4 8.5H10" stroke="#080808" strokeWidth="1.8" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="font-semibold text-forge-white tracking-tight">Forge</span>
        </Link>

        {isLanding && (
          <nav className="hidden md:flex items-center gap-8 text-sm text-forge-subtle">
            <a href="#how" className="hover:text-forge-light transition-colors duration-200">How it works</a>
            <a href="#features" className="hover:text-forge-light transition-colors duration-200">Features</a>
            <a href="#pricing" className="hover:text-forge-light transition-colors duration-200">Pricing</a>
          </nav>
        )}

        <div className="flex items-center gap-3">
          {isLanding ? (
            <>
              <a href="#cta" className="forge-btn-ghost text-sm py-2 px-4">Sign in</a>
              <a href="#cta" className="forge-btn-primary text-sm py-2 px-4">Get started</a>
            </>
          ) : (
            <Link to="/" className="forge-btn-ghost text-sm py-2 px-4">← Back</Link>
          )}
        </div>
      </div>
    </header>
  );
}

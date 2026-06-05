import { useEffect, useRef } from "react";

export function useReveal<T extends HTMLElement = HTMLElement>(threshold = 0.08) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Already visible on mount → reveal immediately with a tiny delay so CSS fires
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight * 0.95) {
      const t = setTimeout(() => el.classList.add("revealed"), 60);
      return () => clearTimeout(t);
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("revealed");
          observer.disconnect();
        }
      },
      { threshold, rootMargin: "0px 0px -40px 0px" }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return ref;
}

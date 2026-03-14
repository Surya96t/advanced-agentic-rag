'use client';

import { useEffect } from 'react';

/** Attaches an IntersectionObserver to all `.reveal` elements, adding `.revealed`
 *  when they scroll into view. Each element is unobserved after it reveals. */
export function useScrollReveal() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1 }
    );

    document.querySelectorAll('.reveal').forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);
}

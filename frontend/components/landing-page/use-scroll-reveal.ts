'use client';

import { useEffect } from 'react';

/**
 * Callback is defined once at module level so it is stable across all hook
 * instances and never re-created during renders.
 */
function handleEntries(entries: IntersectionObserverEntry[]) {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('revealed');
      sharedObserver?.unobserve(entry.target);
    }
  });
}

/** Module-level singleton — created once, shared by every hook invocation. */
let sharedObserver: IntersectionObserver | null = null;

function getObserver(): IntersectionObserver {
  if (!sharedObserver) {
    sharedObserver = new IntersectionObserver(handleEntries, { threshold: 0.1 });
  }
  return sharedObserver;
}

/**
 * Attaches a shared {@link IntersectionObserver} to all unobserved `.reveal`
 * elements, adding `.revealed` when they scroll into view. Elements are
 * skipped if already marked with `data-reveal-observed` to prevent duplicate
 * observation across multiple hook instances.
 */
export function useScrollReveal() {
  useEffect(() => {
    const observer = getObserver();

    document.querySelectorAll<Element>('.reveal').forEach((el) => {
      if (el.hasAttribute('data-reveal-observed')) return;
      el.setAttribute('data-reveal-observed', '');
      observer.observe(el);
    });

    // No disconnect on unmount — the singleton lives for the page lifetime.
    // Individual elements are unobserved after they reveal.
  }, []);
}

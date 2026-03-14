'use client';

import { useEffect, useRef } from 'react';

/**
 * Custom cursor — a dot + lagging cream ring.
 * Scales/changes color when hovering over interactive elements.
 * Hidden on touch devices via CSS.
 */
export function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const dot = dotRef.current;
    const ring = ringRef.current;
    if (!dot || !ring) return;

    let mouseX = 0, mouseY = 0;
    let ringX = 0, ringY = 0;
    let animationId: number;

    const onMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      dot.style.transform = `translate3d(${mouseX}px, ${mouseY}px, 0) translate(-50%, -50%)`;
    };
    window.addEventListener('mousemove', onMouseMove);

    function animateCursor() {
      ringX += (mouseX - ringX) * 0.15;
      ringY += (mouseY - ringY) * 0.15;
      if (ring) ring.style.transform = `translate3d(${ringX}px, ${ringY}px, 0) translate(-50%, -50%)`;
      animationId = requestAnimationFrame(animateCursor);
    }
    animateCursor();

    const clickables = document.querySelectorAll<HTMLElement>('a, button, input, textarea, [data-cursor-pointer]');
    const onEnter = () => {
      ring.style.width = '56px';
      ring.style.height = '56px';
      ring.style.borderColor = 'rgba(252,233,200,0.6)';
      ring.style.backgroundColor = 'rgba(252,233,200,0.05)';
      dot.style.opacity = '0';
    };
    const onLeave = () => {
      ring.style.width = '32px';
      ring.style.height = '32px';
      ring.style.borderColor = 'rgba(255,255,255,0.2)';
      ring.style.backgroundColor = 'transparent';
      dot.style.opacity = '1';
    };
    clickables.forEach(el => {
      el.addEventListener('mouseenter', onEnter);
      el.addEventListener('mouseleave', onLeave);
    });

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      cancelAnimationFrame(animationId);
      clickables.forEach(el => {
        el.removeEventListener('mouseenter', onEnter);
        el.removeEventListener('mouseleave', onLeave);
      });
    };
  }, []);

  return (
    <>
      <div
        ref={dotRef}
        className="hidden md:block fixed top-0 left-0 w-1.5 h-1.5 bg-white rounded-full pointer-events-none z-9999 transition-opacity duration-75"
        style={{ transform: 'translate(-50%, -50%)' }}
      />
      <div
        ref={ringRef}
        className="hidden md:flex fixed top-0 left-0 w-8 h-8 border border-white/20 rounded-full pointer-events-none z-9998 items-center justify-center transition-[width,height,border-color,background-color] duration-300 ease-out"
        style={{ transform: 'translate(-50%, -50%)' }}
      />
    </>
  );
}

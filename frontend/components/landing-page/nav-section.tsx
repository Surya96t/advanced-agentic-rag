'use client';

import Link from 'next/link';
import { Icon } from '@iconify/react';

/**
 * Fixed top navigation bar with logo, pill nav links, and CTAs.
 */
export function NavSection() {
  return (
    <nav className="fixed top-0 w-full z-50 px-6 md:px-12 py-5 flex justify-between items-center bg-[#0a0a0a]/60 backdrop-blur-md border-b border-white/5">
      {/* Logo */}
      <div className="flex items-center gap-3 group cursor-pointer">
        <div className="w-6 h-6 rounded flex items-center justify-center bg-linear-to-tr from-[#fce9c8] to-[#fce9c8]/50 shadow-[0_0_15px_rgba(252,233,200,0.2)] group-hover:shadow-[0_0_25px_rgba(252,233,200,0.4)] transition-shadow duration-500">
          <Icon icon="solar:database-linear" className="text-black text-sm" />
        </div>
        <span className="text-sm font-semibold tracking-tight text-white/90 group-hover:text-white transition-colors">
          Advanced RAG
        </span>
      </div>

      {/* Pill nav */}
      <div className="hidden md:flex items-center gap-8 bg-white/3 border border-white/5 rounded-full px-8 py-2.5 backdrop-blur-sm">
        <a href="#pipeline" className="text-xs font-medium text-white/50 hover:text-white transition-colors tracking-wide">Pipeline</a>
        <a href="#architecture" className="text-xs font-medium text-white/50 hover:text-white transition-colors tracking-wide">Agentic CoT</a>
        <a href="#features" className="text-xs font-medium text-white/50 hover:text-white transition-colors tracking-wide">Features</a>
      </div>

      {/* CTAs */}
      <div className="flex items-center gap-4">
        <a
          href="https://github.com/surya96t/advanced-agentic-rag"
          target="_blank"
          rel="noopener noreferrer"
          className="hidden sm:flex items-center gap-2 text-xs font-medium text-white/70 hover:text-white transition-colors"
        >
          <Icon icon="solar:folder-with-files-linear" />
          View Architecture
        </a>
        <Link
          href="/sign-in"
          className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#fce9c8] text-black hover:bg-[#fce9c8]/90 transition-colors"
        >
          <span className="text-xs font-semibold tracking-tight">Try Me</span>
        </Link>
      </div>
    </nav>
  );
}

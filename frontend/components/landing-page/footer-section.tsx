'use client';

import { Icon } from '@iconify/react';

export function FooterSection() {
  return (
    <footer className="border-t border-white/5 bg-[#050505] py-8 px-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <Icon icon="solar:database-linear" className="text-[#fce9c8] text-lg" />
          <span className="font-semibold text-sm tracking-tight text-white/90">ADVANCED RAG</span>
        </div>

        {/* Tagline */}
        <div className="text-xs uppercase text-white/40 tracking-widest font-mono">
          Open Source Architecture.
        </div>

        {/* GitHub link */}
        <div className="flex gap-5 text-white/40">
          <a
            href="https://github.com/surya96t/advanced-agentic-rag"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white transition-colors cursor-pointer"
            aria-label="GitHub repository"
          >
            <Icon icon="solar:brand-github-linear" className="text-lg" />
          </a>
        </div>
      </div>
    </footer>
  );
}

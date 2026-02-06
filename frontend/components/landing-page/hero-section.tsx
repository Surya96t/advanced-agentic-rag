'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Github } from 'lucide-react';

/**
 * Minimal Hero Section
 * 
 * Simple landing page for a personal RAG portfolio project
 * - Clean title and description
 * - GitHub link
 * - Sign In button
 */
export function HeroSection() {
  return (
    <section className="relative w-full min-h-screen flex items-center justify-center bg-gradient-to-b from-background to-muted/20">
      {/* Subtle grid pattern background */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]" />
      
      {/* Content */}
      <div className="container relative z-10 flex max-w-3xl flex-col items-center justify-center gap-8 px-6 text-center">
        <div className="space-y-4">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Advanced RAG System
          </h1>
          
          <p className="text-lg text-muted-foreground sm:text-xl max-w-2xl">
            A production-grade Retrieval-Augmented Generation system with multi-stage chunking, hybrid search, and agentic workflows.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
          <Button asChild size="lg" variant="outline" className="gap-2">
            <Link href="https://github.com/yourusername/advanced-agentic-rag" target="_blank" rel="noopener noreferrer">
              <Github className="h-5 w-5" />
              View on GitHub
            </Link>
          </Button>

          <Button asChild size="lg">
            <Link href="/sign-in">
              Sign In
            </Link>
          </Button>
        </div>

        {/* Simple 3-step process */}
        <div className="mt-12 flex flex-col sm:flex-row items-center gap-6 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 font-semibold text-primary">1</span>
            <span>Upload Docs</span>
          </div>
          
          <span className="hidden sm:inline text-muted-foreground/40">→</span>
          
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 font-semibold text-primary">2</span>
            <span>Ask Questions</span>
          </div>
          
          <span className="hidden sm:inline text-muted-foreground/40">→</span>
          
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 font-semibold text-primary">3</span>
            <span>Get Answers</span>
          </div>
        </div>
      </div>
    </section>
  );
}

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-linear-to-b from-zinc-50 to-white dark:from-zinc-950 dark:to-black">
      <main className="container flex max-w-4xl flex-col items-center gap-8 px-8 py-16 text-center">
        <h1 className="text-5xl font-bold tracking-tight sm:text-6xl lg:text-7xl">
          Integration Forge
        </h1>
        
        <p className="max-w-2xl text-xl text-muted-foreground sm:text-2xl">
          AI-powered RAG system for synthesizing integration code from siloed API documentation
        </p>

        <div className="flex flex-col gap-4 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/dashboard">
              Get Started
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          
          <Button asChild size="lg" variant="outline">
            <Link href="/sign-in">
              Sign In
            </Link>
          </Button>
        </div>

        <div className="mt-12 grid w-full gap-6 sm:grid-cols-3">
          <div className="rounded-lg border bg-card p-6 text-left">
            <h3 className="mb-2 font-semibold">Multi-Stage Chunking</h3>
            <p className="text-sm text-muted-foreground">
              Advanced document processing with semantic, contextual, and code-aware chunking
            </p>
          </div>
          
          <div className="rounded-lg border bg-card p-6 text-left">
            <h3 className="mb-2 font-semibold">Hybrid Search</h3>
            <p className="text-sm text-muted-foreground">
              Dense vector + sparse text search with RRF fusion and re-ranking
            </p>
          </div>
          
          <div className="rounded-lg border bg-card p-6 text-left">
            <h3 className="mb-2 font-semibold">Agentic RAG</h3>
            <p className="text-sm text-muted-foreground">
              LangGraph-powered agents with query expansion and validation
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

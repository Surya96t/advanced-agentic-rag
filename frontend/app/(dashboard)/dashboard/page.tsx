import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { FileText, MessageSquare, Upload } from 'lucide-react'

export default function DashboardPage() {
  return (
    <div className="container py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold tracking-tight">Welcome to Integration Forge</h1>
        <p className="mt-2 text-lg text-muted-foreground">
          AI-powered RAG system for API documentation synthesis
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Documents Card */}
        <Link
          href="/documents"
          className="group relative overflow-hidden rounded-lg border p-6 transition-colors hover:bg-muted/50"
        >
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <h3 className="mb-2 text-xl font-semibold">Documents</h3>
          <p className="text-sm text-muted-foreground">
            Upload, view, search, and manage your API documentation
          </p>
        </Link>

        {/* Chat Card */}
        <Link
          href="/chat"
          className="group relative overflow-hidden rounded-lg border p-6 transition-colors hover:bg-muted/50"
        >
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <MessageSquare className="h-6 w-6 text-primary" />
          </div>
          <h3 className="mb-2 text-xl font-semibold">Chat Interface</h3>
          <p className="text-sm text-muted-foreground">
            Ask questions and get AI-powered answers from your docs
          </p>
        </Link>
      </div>

      {/* Quick Start */}
      <div className="mt-12 rounded-lg border bg-muted/30 p-6">
        <h2 className="mb-4 text-2xl font-semibold">Quick Start</h2>
        <ol className="space-y-2 text-muted-foreground">
          <li>1. Upload your API documentation (PDF, Markdown, or TXT)</li>
          <li>2. Wait for processing and vectorization</li>
          <li>3. Start chatting to get AI-powered insights</li>
        </ol>
        <div className="mt-6">
          <Button asChild>
            <Link href="/documents">
              <Upload className="mr-2 h-4 w-4" />
              Get Started
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}

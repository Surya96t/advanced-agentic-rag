"use client";

/**
 * Test file to verify AI Elements components are working correctly
 * This file is for verification only and should be deleted after testing
 */

import { Message, MessageContent } from "./message";
import { CodeBlock } from "./code-block";
import { Conversation, ConversationContent, ConversationEmptyState } from "./conversation";
import { InlineCitation } from "./inline-citation";
import { Sources, SourcesTrigger, SourcesContent, Source } from "./sources";
import { Loader } from "./loader";
import { PromptInputTextarea, PromptInputSubmit } from "./prompt-input";
import { Suggestion } from "./suggestion";
import {
  ChainOfThought,
  ChainOfThoughtHeader,
  ChainOfThoughtStep,
  ChainOfThoughtContent,
} from "./chain-of-thought";

/**
 * Test: Basic Message Component
 */
export function TestMessage() {
  return (
    <Message from="assistant">
      <MessageContent>
        <div>This is a test message from the AI assistant.</div>
      </MessageContent>
    </Message>
  );
}

/**
 * Test: Code Block with Copy Button
 */
export function TestCodeBlock() {
  const sampleCode = `function hello() {
  console.log("Hello, World!");
  return "AI Elements is working!";
}`;

  return (
    <CodeBlock 
      language="typescript" 
      code={sampleCode} 
      showLineNumbers 
    />
  );
}

/**
 * Test: Conversation Container
 */
export function TestConversation() {
  return (
    <Conversation>
      <ConversationContent>
        <ConversationEmptyState
          title="Test Conversation"
          description="AI Elements conversation component is working!"
        />
      </ConversationContent>
    </Conversation>
  );
}

/**
 * Test: Inline Citation
 */
export function TestInlineCitation() {
  return (
    <div>
      <p>
        This is a sentence with a citation{" "}
        <InlineCitation>
          <sup className="text-blue-600">[1]</sup>
        </InlineCitation>
        .
      </p>
    </div>
  );
}

/**
 * Test: Sources Component
 */
export function TestSources() {
  return (
    <Sources>
      <SourcesTrigger count={3} />
      <SourcesContent>
        <Source href="https://example.com/doc1" title="Document 1" />
        <Source href="https://example.com/doc2" title="Document 2" />
        <Source href="https://example.com/doc3" title="Document 3" />
      </SourcesContent>
    </Sources>
  );
}

/**
 * Test: Loader Component
 */
export function TestLoader() {
  return <Loader />;
}

/**
 * Test: Prompt Input
 */
export function TestPromptInput() {
  return (
    <form onSubmit={(e) => e.preventDefault()}>
      <PromptInputTextarea placeholder="Type a message..." />
      <PromptInputSubmit status="ready" />
    </form>
  );
}

/**
 * Test: Suggestion Component
 */
export function TestSuggestion() {
  return (
    <div className="flex gap-2">
      <Suggestion 
        suggestion="How do I get started?"
        onClick={(text) => console.log("Clicked:", text)}
      >
        How do I get started?
      </Suggestion>
      <Suggestion 
        suggestion="Show me examples"
        onClick={(text) => console.log("Clicked:", text)}
      >
        Show me examples
      </Suggestion>
    </div>
  );
}

/**
 * Test: Chain of Thought (Agent Pipeline Alternative)
 */
export function TestChainOfThought() {
  return (
    <ChainOfThought>
      <ChainOfThoughtHeader>
        <span>Agent Workflow</span>
      </ChainOfThoughtHeader>
      <ChainOfThoughtContent>
        <ChainOfThoughtStep 
          label="Router" 
          description="Analyzing query..." 
          status="complete"
        />
        <ChainOfThoughtStep 
          label="Retriever" 
          description="Searching documents..." 
          status="active"
        />
        <ChainOfThoughtStep 
          label="Generator" 
          description="Generating response..." 
          status="pending"
        />
        <ChainOfThoughtStep 
          label="Validator" 
          description="Validating output..." 
          status="pending"
        />
      </ChainOfThoughtContent>
    </ChainOfThought>
  );
}

/**
 * All Tests Combined
 */
export function AllComponentTests() {
  return (
    <div className="p-8 space-y-8 max-w-4xl mx-auto">
      <section>
        <h2 className="text-2xl font-bold mb-4">✅ AI Elements Components Test</h2>
        <p className="text-muted-foreground mb-8">
          Verifying all installed components are working correctly
        </p>
      </section>

      <section className="space-y-2">
        <h3 className="text-lg font-semibold">1. Message Component</h3>
        <TestMessage />
      </section>

      <section className="space-y-2">
        <h3 className="text-lg font-semibold">2. Code Block (with Copy Button)</h3>
        <TestCodeBlock />
      </section>

      <section className="space-y-2">
        <h3 className="text-lg font-semibold">3. Conversation Container</h3>
        <div className="h-64 border rounded-lg">
          <TestConversation />
        </div>
      </section>

      <section className="space-y-2">
        <h3 className="text-lg font-semibold">4. Inline Citation</h3>
        <TestInlineCitation />
      </section>

      <section className="space-y-2">
        <h3 className="text-lg font-semibold">5. Sources Component</h3>
        <TestSources />
      </section>

      <section className="space-y-2">
        <h3 className="text-lg font-semibold">6. Loader</h3>
        <TestLoader />
      </section>

      <section className="space-y-2">
        <h3 className="text-lg font-semibold">7. Prompt Input</h3>
        <TestPromptInput />
      </section>

      <section className="space-y-2">
        <h3 className="text-lg font-semibold">8. Suggestion Pills</h3>
        <TestSuggestion />
      </section>

      <section className="space-y-2">
        <h3 className="text-lg font-semibold">9. Chain of Thought (Agent Pipeline)</h3>
        <TestChainOfThought />
      </section>
    </div>
  );
}

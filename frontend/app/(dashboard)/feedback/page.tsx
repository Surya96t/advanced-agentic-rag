"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Label } from "@/components/ui/label"

const feedbackSchema = z.object({
  feedback_type: z.enum(["bug", "feature_request", "general", "other"], {
    required_error: "Please select a feedback type.",
  }),
  message: z.string().min(10, {
    message: "Feedback must be at least 10 characters.",
  }),
  rating: z.coerce.number().min(1).max(5),
})

type FeedbackFormValues = z.infer<typeof feedbackSchema>

export default function FeedbackPage() {
  const [isSubmitting, setIsSubmitting] = useState(false)

  const form = useForm<FeedbackFormValues>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: {
      feedback_type: "general",
      message: "",
      rating: 5,
    },
  })

  async function onSubmit(data: FeedbackFormValues) {
    setIsSubmitting(true)
    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      })

      if (!response.ok) {
        throw new Error("Failed to submit feedback")
      }

      toast.success("Thank you for your feedback!")
      form.reset({
        feedback_type: "general",
        message: "",
        rating: 5,
      })
    } catch (error) {
      toast.error("Something went wrong. Please try again.")
      console.error(error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-140px)] w-full py-6">
      <div className="w-full max-w-lg px-4">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold tracking-tight mb-2">Send Feedback</h1>
          <p className="text-sm text-muted-foreground">
            We value your input! Let us know about any bugs, features you'd like to see, or general thoughts.
          </p>
        </div>
        
        <Card className="border-none shadow-none bg-transparent">
          <CardContent className="p-0">
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
                <FormField
                  control={form.control}
                  name="feedback_type"
                  render={({ field }) => (
                    <FormItem className="space-y-3">
                      <FormLabel className="text-sm font-medium">Feedback Type</FormLabel>
                      <FormControl>
                        <RadioGroup
                          onValueChange={field.onChange}
                          value={field.value}
                          className="grid grid-cols-2 gap-3 sm:grid-cols-4"
                        >
                        >
                          <FormItem>
                            <FormControl>
                              <RadioGroupItem value="bug" className="peer sr-only" />
                            </FormControl>
                            <FormLabel className="flex flex-col items-center justify-center rounded-md border border-muted bg-popover p-2 h-16 text-center hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-accent peer-data-[state=checked]:text-accent-foreground cursor-pointer transition-all">
                              <span className="text-xs font-medium">Bug Report</span>
                            </FormLabel>
                          </FormItem>
                          <FormItem>
                            <FormControl>
                              <RadioGroupItem value="feature_request" className="peer sr-only" />
                            </FormControl>
                            <FormLabel className="flex flex-col items-center justify-center rounded-md border border-muted bg-popover p-2 h-16 text-center hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-accent peer-data-[state=checked]:text-accent-foreground cursor-pointer transition-all">
                              <span className="text-xs font-medium">Feature</span>
                            </FormLabel>
                          </FormItem>
                          <FormItem>
                            <FormControl>
                              <RadioGroupItem value="general" className="peer sr-only" />
                            </FormControl>
                            <FormLabel className="flex flex-col items-center justify-center rounded-md border border-muted bg-popover p-2 h-16 text-center hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-accent peer-data-[state=checked]:text-accent-foreground cursor-pointer transition-all">
                              <span className="text-xs font-medium">General</span>
                            </FormLabel>
                          </FormItem>
                          <FormItem>
                            <FormControl>
                              <RadioGroupItem value="other" className="peer sr-only" />
                            </FormControl>
                            <FormLabel className="flex flex-col items-center justify-center rounded-md border border-muted bg-popover p-2 h-16 text-center hover:bg-accent hover:text-accent-foreground peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-accent peer-data-[state=checked]:text-accent-foreground cursor-pointer transition-all">
                              <span className="text-xs font-medium">Other</span>
                            </FormLabel>
                          </FormItem>
                        </RadioGroup>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="message"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-sm font-medium">Message</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="Tell us what you think..."
                          className="resize-none min-h-[100px] text-sm"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <Label className="text-sm font-medium">Rating</Label>
                    <span className="text-xs text-muted-foreground">
                      {form.watch("rating") === 1 ? "Poor" : 
                       form.watch("rating") === 5 ? "Excellent" : 
                       `${form.watch("rating")} / 5`}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Button
                        key={star}
                        type="button"
                        variant={form.watch("rating") === star ? "default" : "outline"}
                        className="h-10 flex-1 transition-all text-sm font-medium"
                        onClick={() => form.setValue("rating", star)}
                      >
                        {star}
                      </Button>
                    ))}
                  </div>
                </div>

                <Button type="submit" disabled={isSubmitting} className="w-full h-10 text-sm font-medium mt-2">
                  {isSubmitting && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
                  Submit Feedback
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}


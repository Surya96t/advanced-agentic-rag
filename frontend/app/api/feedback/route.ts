
import { type NextRequest } from "next/server";
import { apiFetch } from "@/lib/api-client";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const response = await apiFetch("api/v1/feedback", {
      method: "POST",
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      if (response.status === 401) {
        return new Response("Unauthorized", { status: 401 });
      }
      return new Response(await response.text(), { status: response.status });
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error("Feedback error:", error);
    return new Response("Internal Server Error", { status: 500 });
  }
}

export async function GET() {
  try {
    const response = await apiFetch("api/v1/feedback");

    if (!response.ok) {
      if (response.status === 401) {
        return new Response("Unauthorized", { status: 401 });
      }
      return new Response(await response.text(), { status: response.status });
    }

    const data = await response.json();
    return Response.json(data);
  } catch (error) {
    console.error("Feedback error:", error);
    return new Response("Internal Server Error", { status: 500 });
  }
}

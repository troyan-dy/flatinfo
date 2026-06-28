import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

// Прокси к бэкенду: клиент не знает адрес бэкенда и не зависит от CORS.
export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q") ?? "";
  if (q.trim().length < 3) return NextResponse.json([]);
  try {
    const resp = await fetch(
      `${BACKEND_URL}/api/suggest?q=${encodeURIComponent(q)}`,
      { cache: "no-store" },
    );
    if (!resp.ok) return NextResponse.json([]);
    return NextResponse.json(await resp.json());
  } catch {
    return NextResponse.json([]);
  }
}

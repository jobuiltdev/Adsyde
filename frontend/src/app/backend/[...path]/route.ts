import type { NextRequest } from "next/server";

const server = (process.env.API_SERVER_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const target = `${server}/${path.join("/")}/${request.nextUrl.search}`;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");
  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer();
  const upstream = await fetch(target, { method: request.method, headers, body, redirect: "manual", cache: "no-store" });
  const responseHeaders = new Headers();
  for (const name of ["content-type", "content-disposition", "cache-control", "x-request-id"]) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const HEAD = proxy;

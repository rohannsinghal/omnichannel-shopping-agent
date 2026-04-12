// src/app/page.js  — SERVER COMPONENT (no "use client")
// Fetches real products from MongoDB at build/request time.
// The carousel sections are split into a client component for interactivity.

import HomeClient from "@/components/HomeClient";

async function getProducts() {
  try {
    // Call our own Next.js API route (created below as /api/products/route.js)
    // During SSR this hits the same process, so localhost works fine.
    const res = await fetch(`${process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000"}/api/products?limit=12`, {
      cache: "no-store", // always fresh — swap to revalidate:3600 for production
    });
    if (!res.ok) throw new Error("Failed to fetch");
    const data = await res.json();
    return data.products || [];
  } catch (e) {
    console.error("getProducts error:", e);
    return [];
  }
}

export default async function HomePage() {
  const products = await getProducts();
  return <HomeClient products={products} />;
}
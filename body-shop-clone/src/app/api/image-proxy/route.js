// src/app/api/image-proxy/route.js
import { NextResponse } from "next/server";

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const imageUrl = searchParams.get("url");

  if (!imageUrl) return new NextResponse("Missing URL", { status: 400 });

  try {
    // Spoof a real browser to bypass Hotlink protection
    const response = await fetch(imageUrl, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://www.nykaa.com/" // Pretend we are coming from Nykaa itself
      },
    });

    if (!response.ok) {
      throw new Error(`Image fetch failed with status: ${response.status}`);
    }

    const arrayBuffer = await response.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    return new NextResponse(buffer, {
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "image/jpeg",
        "Cache-Control": "public, max-age=86400", 
      },
    });
  } catch (error) {
    console.error("Proxy Error:", error.message);
    return new NextResponse("Error fetching image", { status: 500 });
  }
}
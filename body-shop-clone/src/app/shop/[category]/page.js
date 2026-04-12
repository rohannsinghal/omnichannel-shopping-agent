// src/app/shop/[category]/page.js
// Handles: /shop/skincare  /shop/body  /shop/hair  /shop/fragrance  etc.

import ShopClient from "@/components/ShopClient";

const CATEGORY_MAP = {
  skincare:  { label: "Face & Skincare", mongo: "Skincare",  banner: "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?w=1400&q=80" },
  body:      { label: "Bath & Body",     mongo: "Body",      banner: "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=1400&q=80" },
  hair:      { label: "Hair Care",       mongo: "Hair",      banner: "https://images.unsplash.com/photo-1527799820374-dcf8d9d4a388?w=1400&q=80" },
  fragrance: { label: "Fragrance",       mongo: "Fragrance", banner: "https://images.unsplash.com/photo-1592945403244-b3fbafd7f539?w=1400&q=80" },
  range:     { label: "All Ranges",      mongo: null,        banner: "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=1400&q=80" },
  gifts:     { label: "Gifts",           mongo: "Gift",      banner: "https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=1400&q=80" },
};

async function getProducts(categorySlug, searchParams) {
  const meta     = CATEGORY_MAP[categorySlug] || { label: categorySlug, mongo: null };
  const category = meta.mongo || categorySlug;
  const search   = searchParams?.search || "";
  const limit    = 50;

  try {
    const qs = new URLSearchParams({ limit, category });
    if (search) qs.set("search", search);

    const res = await fetch(
      `${process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000"}/api/products?${qs}`,
      { cache: "no-store" }
    );
    const data = await res.json();
    return data.products || [];
  } catch {
    return [];
  }
}

export default async function ShopPage({ params, searchParams }) {
  const { category } = await params;
  const sp = await searchParams;
  const meta     = CATEGORY_MAP[category] || { label: category, mongo: null, banner: "https://images.unsplash.com/photo-1556228578-8c89e6adf883?w=1400&q=80" };
  const products = await getProducts(category, sp);

  return (
    <ShopClient
      products={products}
      categoryLabel={meta.label}
      bannerImg={meta.banner}
      categorySlug={category}
    />
  );
}

export async function generateMetadata({ params }) {

  const resolvedParams = await params;

  const meta = CATEGORY_MAP[resolvedParams.category] || { label: resolvedParams.category };
  return { title: `${meta.label} | The Body Shop` };
}
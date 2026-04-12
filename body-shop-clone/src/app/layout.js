import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ChatWidget from "@/components/ChatWidget";

export const metadata = {
  title: "The Body Shop® | Cruelty-Free & Natural Beauty Products",
  description: "Shop cruelty-free skincare, body care, hair care, fragrance and gifts at The Body Shop India. Ethically sourced, naturally inspired beauty.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body style={{ margin: 0, padding: 0, backgroundColor: "#fff" }}>
        <Navbar />
        <main style={{ minHeight: "60vh" }}>{children}</main>
        <Footer />
        <ChatWidget />
      </body>
    </html>
  );
}
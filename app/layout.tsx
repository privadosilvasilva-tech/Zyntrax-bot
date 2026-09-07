import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Suporte Bot",
  description: "Chat ao vivo e suporte para o servidor Discord",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}

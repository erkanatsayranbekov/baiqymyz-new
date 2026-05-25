import "~/styles/globals.css";
import type { Metadata } from "next";
import { Montserrat } from "next/font/google";
import ClientLayout from "./ClientLayout";

export const metadata: Metadata = {
  title: "Baiqymyz",
  description: "Baiqymyz",
  icons: [{ rel: "icon", url: "/favicon.ico" }],
};

const montserrat = Montserrat({
  subsets: ["cyrillic", "latin"],
  variable: "--font-montserrat-sans",
});

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="kz" className={`${montserrat.variable}`}>
      <body>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}

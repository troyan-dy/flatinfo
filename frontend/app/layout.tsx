import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "flatinfo — снимать или покупать?",
  description:
    "Введите адрес — узнайте, что выгоднее по деньгам: снимать жильё или брать ипотеку. Честный расчёт по методологии нетто-богатства.",
  openGraph: {
    title: "flatinfo — снимать или покупать?",
    description:
      "По адресу считаем, что выгоднее: снимать жильё или купить в ипотеку. Учитываем рост цен, аренды и доход от вложений.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}

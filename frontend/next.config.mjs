/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Минимальный self-contained сервер: .next/standalone тащит только реально
  // используемые зависимости (без dev). Рантайм-образ ~200 МБ вместо ~1.2 ГБ —
  // критично для маленького диска сервера и быстрых пересборок по cron.
  output: "standalone",
};

export default nextConfig;

import { createClient } from "@insforge/sdk";

const baseUrl =
  process.env.NEXT_PUBLIC_INSFORGE_BASE_URL ||
  "https://4fwr5aay.us-east.insforge.app";
const anonKey =
  process.env.NEXT_PUBLIC_INSFORGE_ANON_KEY ||
  "anon_c9d15cd959cd12c8977b06e38910210faf38037b607f8990378411f6c7fa682c";

export const insforge = createClient({
  baseUrl,
  anonKey,
});

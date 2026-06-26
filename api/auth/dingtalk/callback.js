import { handleDingTalkLoginCallback } from "../../../lib/dingtalk-auth.js";

export default async function handler(req, res) {
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });
  const params = new URLSearchParams();
  Object.entries(req.query || {}).forEach(([key, value]) => {
    params.set(key, Array.isArray(value) ? value[0] : value);
  });
  const targetUrl = await handleDingTalkLoginCallback(req, params);
  res.redirect(302, targetUrl);
}

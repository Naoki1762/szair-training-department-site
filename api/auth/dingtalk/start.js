import {
  buildDingTalkLoginUrl,
  buildSiteRedirect
} from "../../../lib/dingtalk-auth.js";

export default function handler(req, res) {
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });
  try {
    res.redirect(302, buildDingTalkLoginUrl(req, "/api/auth/dingtalk/callback"));
  } catch (error) {
    res.redirect(302, buildSiteRedirect({ error: error.message || "钉钉一键登录尚未配置" }));
  }
}

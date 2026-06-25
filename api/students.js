import {
  getDingTalkStudents,
  hasStudentSyncConfig,
  isAuthorizedStudentRequest
} from "../lib/dingtalk-students.js";

export default async function handler(req, res) {
  applyCors(req, res);

  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).json({ error: "Method not allowed" });

  if (!hasStudentSyncConfig()) {
    return res.status(503).json({
      error: "钉钉学员同步尚未配置",
      code: "STUDENT_SYNC_NOT_CONFIGURED"
    });
  }

  if (!isAuthorizedStudentRequest(req.headers["x-student-view-token"])) {
    return res.status(401).json({ error: "访问口令不正确", code: "UNAUTHORIZED" });
  }

  try {
    const data = await getDingTalkStudents({ force: req.query.refresh === "1" });
    return res.status(200).json(data);
  } catch (error) {
    console.error(error);
    return res.status(502).json({ error: error.message || "钉钉同步失败" });
  }
}

function applyCors(req, res) {
  const origin = req.headers.origin || "";
  const allowedOrigins = new Set([
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "https://naoki1762.github.io",
    "https://ytewdgujhvdss-cyber.github.io"
  ]);

  if (allowedOrigins.has(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Vary", "Origin");
  }
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, X-Student-View-Token");
}

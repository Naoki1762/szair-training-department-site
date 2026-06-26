import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";

const DEFAULT_SITE_URL = "https://naoki1762.github.io/szair-training-department-site/";
const DEFAULT_SCOPE = "openid";

export function hasDingTalkLoginConfig() {
  return Boolean(
    process.env.DINGTALK_CLIENT_ID
    && process.env.DINGTALK_CLIENT_SECRET
  );
}

export function buildDingTalkLoginUrl(req, callbackPath = "/api/auth/dingtalk/callback") {
  if (!hasDingTalkLoginConfig()) {
    throw new Error("钉钉一键登录尚未配置");
  }

  const redirectUri = getCallbackUrl(req, callbackPath);
  const state = signState({
    nonce: randomBytes(12).toString("base64url"),
    next: getSiteUrl(),
    ts: Date.now()
  });
  const url = new URL("https://login.dingtalk.com/oauth2/auth");
  url.searchParams.set("client_id", process.env.DINGTALK_CLIENT_ID);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("scope", process.env.DINGTALK_LOGIN_SCOPE || DEFAULT_SCOPE);
  url.searchParams.set("prompt", process.env.DINGTALK_LOGIN_PROMPT || "consent");
  url.searchParams.set("state", state);
  return url.toString();
}

export async function handleDingTalkLoginCallback(req, query) {
  const code = String(query.get("authCode") || query.get("code") || "").trim();
  const state = String(query.get("state") || "").trim();
  if (!code) return buildSiteRedirect({ error: "钉钉未返回授权码" });

  const statePayload = verifyState(state);
  if (!statePayload) return buildSiteRedirect({ error: "钉钉登录状态校验失败" });

  try {
    const token = await exchangeUserAccessToken(code);
    const profile = await getDingTalkUserProfile(token.accessToken);
    const session = buildLoginSession(profile);
    return buildSiteRedirect({ session, next: statePayload.next });
  } catch (error) {
    return buildSiteRedirect({ error: error.message || "钉钉登录失败" });
  }
}

export function buildSiteRedirect({ session = null, error = "", next = "" } = {}) {
  const siteUrl = new URL(next || getSiteUrl());
  const hash = new URLSearchParams();
  if (session) hash.set("dingtalk_session", session);
  if (error) hash.set("dingtalk_error", error);
  siteUrl.hash = hash.toString();
  return siteUrl.toString();
}

function getCallbackUrl(req, callbackPath) {
  if (process.env.DINGTALK_AUTH_REDIRECT_URI) return process.env.DINGTALK_AUTH_REDIRECT_URI;
  const host = req.headers["x-forwarded-host"] || req.headers.host;
  const proto = req.headers["x-forwarded-proto"] || "https";
  return `${proto}://${host}${callbackPath}`;
}

function getSiteUrl() {
  return process.env.PUBLIC_SITE_URL || DEFAULT_SITE_URL;
}

async function exchangeUserAccessToken(code) {
  const response = await fetch("https://api.dingtalk.com/v1.0/oauth2/userAccessToken", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      clientId: process.env.DINGTALK_CLIENT_ID,
      clientSecret: process.env.DINGTALK_CLIENT_SECRET,
      code,
      grantType: "authorization_code"
    })
  });
  const data = await parseResponse(response, "获取钉钉用户访问凭证");
  if (!data.accessToken) throw new Error("钉钉未返回用户访问凭证");
  return data;
}

async function getDingTalkUserProfile(userAccessToken) {
  const response = await fetch("https://api.dingtalk.com/v1.0/contact/users/me", {
    headers: {
      "x-acs-dingtalk-access-token": userAccessToken
    }
  });
  const data = await parseResponse(response, "获取钉钉登录用户信息");
  return {
    userId: String(data.userId || data.userid || data.openId || ""),
    unionId: String(data.unionId || ""),
    name: String(data.nick || data.name || data.mobile || "钉钉用户"),
    avatar: String(data.avatarUrl || data.avatar || ""),
    mobile: String(data.mobile || ""),
    email: String(data.email || "")
  };
}

function buildLoginSession(profile) {
  const adminIds = parseCsv(process.env.DINGTALK_ADMIN_USER_IDS);
  const adminUnionIds = parseCsv(process.env.DINGTALK_ADMIN_UNION_IDS);
  const isAdmin = adminIds.has(profile.userId) || adminUnionIds.has(profile.unionId);
  const payload = {
    provider: "dingtalk",
    sub: profile.userId || profile.unionId,
    userId: profile.userId,
    unionId: profile.unionId,
    name: profile.name,
    avatar: profile.avatar,
    role: isAdmin ? "manager" : "student",
    roleName: isAdmin ? "部门行政人员" : "飞行学员",
    iat: Date.now(),
    exp: Date.now() + 8 * 60 * 60 * 1000
  };
  return signPayload(payload);
}

function parseCsv(value = "") {
  return new Set(String(value).split(",").map(item => item.trim()).filter(Boolean));
}

function signState(payload) {
  return signPayload(payload);
}

function verifyState(token) {
  const payload = verifyPayload(token);
  if (!payload) return null;
  if (Date.now() - Number(payload.ts || 0) > 10 * 60 * 1000) return null;
  return payload;
}

function signPayload(payload) {
  const encoded = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const signature = createHmac("sha256", getSessionSecret()).update(encoded).digest("base64url");
  return `${encoded}.${signature}`;
}

function verifyPayload(token) {
  const [encoded, signature] = String(token || "").split(".");
  if (!encoded || !signature) return null;
  const expected = createHmac("sha256", getSessionSecret()).update(encoded).digest("base64url");
  if (!safeEqual(signature, expected)) return null;
  try {
    return JSON.parse(Buffer.from(encoded, "base64url").toString("utf8"));
  } catch {
    return null;
  }
}

function getSessionSecret() {
  return process.env.DINGTALK_AUTH_SESSION_SECRET
    || process.env.DINGTALK_STUDENT_VIEW_TOKEN
    || process.env.DINGTALK_CLIENT_SECRET
    || "local-dev-only";
}

function safeEqual(left, right) {
  const leftBuffer = Buffer.from(String(left));
  const rightBuffer = Buffer.from(String(right));
  return leftBuffer.length === rightBuffer.length && timingSafeEqual(leftBuffer, rightBuffer);
}

async function parseResponse(response, action) {
  const text = await response.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`${action}失败：HTTP ${response.status}`);
  }
  if (!response.ok) {
    throw new Error(`${action}失败：HTTP ${response.status} ${data.message || data.errmsg || ""}`.trim());
  }
  return data;
}

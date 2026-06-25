import { timingSafeEqual } from "node:crypto";

const ROOT_DEPARTMENT_ID = 1;
const PAGE_SIZE = 100;
const CACHE_TTL_MS = 5 * 60 * 1000;

let cache = null;

export function hasStudentSyncConfig() {
  return Boolean(
    process.env.DINGTALK_CLIENT_ID
    && process.env.DINGTALK_CLIENT_SECRET
    && process.env.DINGTALK_STUDENT_VIEW_TOKEN
  );
}

export function isAuthorizedStudentRequest(token) {
  const expected = process.env.DINGTALK_STUDENT_VIEW_TOKEN || "";
  const received = String(token || "");
  if (!expected || !received) return false;

  const expectedBuffer = Buffer.from(expected);
  const receivedBuffer = Buffer.from(received);
  return expectedBuffer.length === receivedBuffer.length
    && timingSafeEqual(expectedBuffer, receivedBuffer);
}

export async function getDingTalkStudents({ force = false } = {}) {
  if (!hasStudentSyncConfig()) {
    return {
      configured: false,
      departmentName: getTargetDepartmentName(),
      students: [],
      syncedAt: null
    };
  }

  if (!force && cache && Date.now() - cache.cachedAt < CACHE_TTL_MS) {
    return cache.payload;
  }

  const accessToken = await getDingTalkAccessToken();
  const department = await findDepartmentByName(accessToken, getTargetDepartmentName());
  if (!department) {
    throw new Error(`未在钉钉通讯录中找到部门“${getTargetDepartmentName()}”`);
  }

  const users = await listDepartmentUsers(accessToken, department.deptId);
  const syncedAt = new Date().toISOString();
  const payload = {
    configured: true,
    departmentName: department.name,
    departmentId: department.deptId,
    students: users.map(normalizeStudent),
    syncedAt
  };

  cache = { cachedAt: Date.now(), payload };
  return payload;
}

function getTargetDepartmentName() {
  return process.env.DINGTALK_STUDENT_DEPARTMENT_NAME || "飞行学员管理室";
}

async function getDingTalkAccessToken() {
  const response = await fetch("https://api.dingtalk.com/v1.0/oauth2/accessToken", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      appKey: process.env.DINGTALK_CLIENT_ID,
      appSecret: process.env.DINGTALK_CLIENT_SECRET
    })
  });
  const data = await parseResponse(response, "获取钉钉访问令牌");
  if (!data.accessToken) throw new Error("钉钉未返回 accessToken");
  return data.accessToken;
}

async function findDepartmentByName(accessToken, targetName) {
  const queue = [ROOT_DEPARTMENT_ID];
  const visited = new Set();

  while (queue.length) {
    const parentId = queue.shift();
    if (visited.has(parentId)) continue;
    visited.add(parentId);

    const children = await listChildDepartments(accessToken, parentId);
    const match = children.find(item => item.name.trim() === targetName.trim());
    if (match) return match;
    children.forEach(item => queue.push(item.deptId));
  }

  return null;
}

async function listChildDepartments(accessToken, departmentId) {
  const data = await callTopApi(
    "https://oapi.dingtalk.com/topapi/v2/department/listsub",
    accessToken,
    { dept_id: departmentId }
  );
  return (data.result || []).map(item => ({
    deptId: Number(item.dept_id),
    name: String(item.name || ""),
    parentId: Number(item.parent_id || 0)
  }));
}

async function listDepartmentUsers(accessToken, departmentId) {
  const users = [];
  let cursor = 0;
  let hasMore = true;

  while (hasMore) {
    const data = await callTopApi(
      "https://oapi.dingtalk.com/topapi/v2/user/list",
      accessToken,
      {
        dept_id: departmentId,
        cursor,
        size: PAGE_SIZE,
        order_field: "entry_asc",
        contain_access_limit: false
      }
    );
    const result = data.result || {};
    users.push(...(result.list || []));
    hasMore = Boolean(result.has_more);
    cursor = Number(result.next_cursor || 0);
  }

  return users;
}

async function callTopApi(endpoint, accessToken, body) {
  const url = new URL(endpoint);
  url.searchParams.set("access_token", accessToken);
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await parseResponse(response, "调用钉钉通讯录接口");
  if (data.errcode && data.errcode !== 0) {
    throw new Error(`钉钉接口错误 ${data.errcode}：${data.errmsg || "未知错误"}`);
  }
  return data;
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

function normalizeStudent(user) {
  return {
    userId: String(user.userid || ""),
    name: String(user.name || ""),
    title: String(user.title || "在队学员"),
    jobNumber: String(user.job_number || ""),
    active: user.active !== false,
    avatar: String(user.avatar || "")
  };
}

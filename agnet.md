# 项目协作说明

## 项目概况

本项目是深圳航空培训部管理平台，当前真实仓库路径：

```text
/Users/lishu/Documents/Codex/2026-06-25/wo-xia/work/szair-training-department-site
```

远端仓库：

```text
https://github.com/Naoki1762/szair-training-department-site.git
```

线上静态页面：

```text
https://naoki1762.github.io/szair-training-department-site/
```

Render 后端服务：

```text
https://training-qa-api-naoki1762.onrender.com
```

后续沟通默认使用中文。网站修改完成后需要提交并推送到 GitHub。

## 当前技术栈

- Django 5.2.15：后台管理、数据库、接口
- SQLite：本地开发数据库，文件为 `db.sqlite3`，不提交 Git
- Vue 3.5.39 + Vite 8.1.0：前台构建层
- 原 Node 后端文件仍保留：`server.js`、`api/`、`lib/`

## 重要目录

- `training_platform/`：Django 项目配置
- `portal/`：Django 应用、模型、后台管理、接口、管理命令
- `frontend/`：Vue 前台源码
- `dist/`：Vue/Vite 构建产物，Django 首页优先渲染这里的 `index.html`
- `assets/`：图片、作风量化规则、问答配置等静态资源
- `index.html`：原静态版本兼容入口，暂时保留
- `DJANGO_SETUP.md`：Django 运行和后台说明

如果当前终端或 Finder 在 `/Users/lishu/Documents/培训部管理平台`，需要切到真实仓库路径才能看到 `frontend/` 等项目文件。

## 本地启动

```bash
cd /Users/lishu/Documents/Codex/2026-06-25/wo-xia/work/szair-training-department-site
source .venv/bin/activate
pip install -r requirements.txt
npm install
npm run build
python manage.py runserver 127.0.0.1:8000
```

前端首页：

```text
http://127.0.0.1:8000/
```

管理后台：

```text
http://127.0.0.1:8000/admin/
```

本地后台管理员账号：

```text
用户名：admin
密码：shfx6688
```

## 数据库初始化

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py import_conduct_rules
python manage.py seed_demo_people --count 300
```

说明：

- `import_conduct_rules` 从 `assets/conduct-rules.js` 导入 97 条作风量化规则。
- `seed_demo_people` 生成 300 名测试学员和 4 名管理人员。
- 当前 `/api/students` 已从 Django 数据库返回学员、阶段、作风分和作风记录。

## 已完成的关键功能

- 钉钉通讯录同步接口和钉钉 OAuth 入口已保留。
- 在队学员 300 人测试名单可初始化到数据库。
- 学员作风分系统已建立：S1/S2/S3/S4 阶段，行政人员不计分，学员初始 100 分。
- 作风分制度项目来自《飞行学员安全作风量化管理规定2026.6》附表一 97 条规则。
- 前台首页已有“进入管理后台”入口。
- Django Admin 可管理科室/部门、人员档案、学员档案、作风量化规则、作风分记录和登录审计。

## 备份与回退

改造前版本已备份：

- Git 标签：`v1.0`
- Git 分支：`backup/v1.0`

## 开发注意事项

- 不要提交 `.venv/`、`db.sqlite3`、`node_modules/`、`staticfiles/`。
- 前台视觉暂时不要随意调整；如修改前台，需要同步修改 `frontend/index.html`，再运行 `npm run build` 更新 `dist/`。
- 后台数据结构修改后需要执行 `python manage.py makemigrations`，并提交迁移文件。
- 修改完成后至少运行：

```bash
source .venv/bin/activate
python manage.py check
python manage.py test portal
```

涉及前台构建时还要运行：

```bash
npm run build
```

# Django 项目运行说明

当前仓库已增加 Django 项目 `training_platform` 和应用 `portal`。

改造前版本已经备份为：

- Git 标签：`v1.0`
- Git 分支：`backup/v1.0`

## 本地启动

```bash
cd /Users/lishu/Documents/Codex/2026-06-25/wo-xia/work/szair-training-department-site
source .venv/bin/activate
pip install -r requirements.txt
npm install
npm run build
python manage.py runserver 127.0.0.1:8000
```

打开：

```text
http://127.0.0.1:8000/
```

## 管理后台

后台入口：

```text
http://127.0.0.1:8000/admin/
```

本地开发管理员账号已经写入本机 `db.sqlite3`：

```text
用户名：admin
密码：shfx6688
```

后台目前可以管理：

- 科室/部门
- 人员档案
- 学员档案
- 作风量化规则
- 作风分记录
- 登录审计

本地数据库初始化命令：

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py import_conduct_rules
python manage.py seed_demo_people --count 300
```

其中 `import_conduct_rules` 会从 `assets/conduct-rules.js` 导入 97 条《飞行学员安全作风量化管理规定2026.6》规则。

## MySQL 数据库

当前项目已支持 MySQL。多人正式使用时请在 `.env` 中启用：

```text
DB_ENGINE=mysql
MYSQL_DATABASE=szair_training
MYSQL_USER=szair_training
MYSQL_PASSWORD=请填写MySQL密码
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```

首次使用 MySQL 前，需要先在 MySQL 中创建数据库和账号，例如：

```sql
CREATE DATABASE szair_training CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'szair_training'@'%' IDENTIFIED BY '请填写MySQL密码';
GRANT ALL PRIVILEGES ON szair_training.* TO 'szair_training'@'%';
FLUSH PRIVILEGES;
```

然后执行：

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py import_conduct_rules
python manage.py seed_demo_people --count 300
```

如果没有配置 `DB_ENGINE=mysql`，项目会继续使用本地 SQLite 作为开发兜底。

## 本地虚拟科室数据库

在真实科室数据库准备好之前，可以先用 Docker 启动一个本地虚拟 MySQL。详见：

```text
LOCAL_MYSQL.md
```

本地虚拟数据库配置模板：

```text
.env.mysql.example
```

## 当前迁移范围

- `/` 由 Django 应用优先渲染 Vue/Vite 构建后的 `dist/index.html`。
- Vue 前台源码位于 `frontend/`，构建命令为 `npm run build`。
- `/assets/...` 继续服务原有静态资源。
- `/api/qa/ask` 已提供 Django 本地演示问答接口。
- `/api/students` 已接入 Django 数据库，可返回学员档案、阶段、作风分和作风记录。
- `/api/auth/dingtalk/start` 默认跳转到现有 Render 钉钉登录入口，避免打断线上登录。

根目录 `index.html` 暂时保留为改造前静态版本和 GitHub Pages 兼容入口。Vue 构建产物保持现有页面结构、样式和业务脚本不变，只增加 Vue 运行时入口。

原 Node 后端文件暂时保留，用作线上 Render API 的稳定备份与后续迁移参照。

## 前端文件夹

前端文件夹在真实项目仓库里：

```text
/Users/lishu/Documents/Codex/2026-06-25/wo-xia/work/szair-training-department-site/frontend
```

如果当前 Finder 或终端停在 `/Users/lishu/Documents/培训部管理平台`，需要先进入上面的真实仓库路径才能看到 `frontend/`。

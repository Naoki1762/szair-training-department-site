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

## 当前迁移范围

- `/` 由 Django 应用优先渲染 Vue/Vite 构建后的 `dist/index.html`。
- Vue 前台源码位于 `frontend/`，构建命令为 `npm run build`。
- `/assets/...` 继续服务原有静态资源。
- `/api/qa/ask` 已提供 Django 本地演示问答接口。
- `/api/students` 已保留 Django 路由占位，待迁移钉钉通讯录凭证与同步逻辑。
- `/api/auth/dingtalk/start` 默认跳转到现有 Render 钉钉登录入口，避免打断线上登录。

根目录 `index.html` 暂时保留为改造前静态版本和 GitHub Pages 兼容入口。Vue 构建产物保持现有页面结构、样式和业务脚本不变，只增加 Vue 运行时入口。

原 Node 后端文件暂时保留，用作线上 Render API 的稳定备份与后续迁移参照。

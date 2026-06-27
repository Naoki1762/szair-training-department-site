# 本地虚拟科室 MySQL 数据库

这个文件用于把本机模拟成“科室已有一台 MySQL 数据库”。等真实科室数据库准备好后，只需要替换 `.env` 里的连接信息，不需要改代码。

## 需要先安装

本机当前还没有 Docker。请先安装：

```text
Docker Desktop for Mac
```

安装完成后，在终端确认：

```bash
docker --version
docker compose version
```

## 启动虚拟 MySQL

```bash
cd /Users/lishu/Documents/Codex/2026-06-25/wo-xia/work/szair-training-department-site
cp .env.mysql.example .env
docker compose up -d mysql
```

本地虚拟数据库连接信息：

```text
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_DATABASE=szair_training
MYSQL_USER=szair_training
MYSQL_PASSWORD=szair_training_dev_2026
```

Navicat/DBeaver 连接时也用上面这组信息。

## 初始化数据库

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py import_conduct_rules
python manage.py seed_demo_people --count 300
python manage.py ensure_admin_user
```

后台账号：

```text
用户名：admin
密码：shfx6688
```

## 启动网站

```bash
npm run build
python manage.py runserver 127.0.0.1:8000
```

访问：

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/admin/
```

## 将来接入真实科室数据库

真实数据库准备好后，只改 `.env`：

```text
DB_ENGINE=mysql
MYSQL_DATABASE=真实数据库名
MYSQL_USER=真实数据库用户
MYSQL_PASSWORD=真实数据库密码
MYSQL_HOST=真实数据库内网IP或域名
MYSQL_PORT=3306
```

然后执行：

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py import_conduct_rules
python manage.py ensure_admin_user
```

如果要把本地虚拟库里的数据迁到真实库，可以再做一次数据导出/导入。

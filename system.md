# Kiến trúc toàn diện — frappe_docker / ERPNext

---

## 1. Bức tranh tổng thể

Repo này **không chứa code ERPNext** — đây là lớp **Docker orchestration**. Ứng dụng thực sự nằm ở 3 repo riêng biệt:

```
frappe/frappe        ← Framework (Python web framework, ORM, DocType engine)
frappe/erpnext       ← App ERP (Accounting, HR, Inventory, Manufacturing...)
frappe/frappe_docker ← Repo này: infrastructure để chạy hai thứ trên
```

---

## 2. Luồng khởi động (startup flow)

```
docker compose up
       │
       ▼
  configurator ──► writes common_site_config.json (DB host, Redis URLs)
       │               (exits with code 0)
       ▼
  ┌────────────────────────────────────────────────┐
  │  backend   websocket   queue-short   queue-long │
  │                        scheduler               │
  └────────────────────────────────────────────────┘
       │
       ▼
  frontend (nginx) ──► proxies /api/* → backend:8000
                                /socket.io → websocket:9000
                                static assets từ sites volume
```

Tất cả services dùng **cùng 1 image** (`frappe/erpnext`), khác nhau chỉ ở `command` được gọi.

---

## 3. Image hierarchy

```
images/
├── bench/          ← Development only (pyenv, nvm, full toolchain, sudo)
│                     Ports: 8000-8005, 9000-9005, 6787
│
├── production/     ← 4-stage build: base → build → builder → erpnext
│                     Self-contained: Frappe + ERPNext pre-installed
│                     Không customizable (không đọc apps.json)
│
├── custom/         ← 2-stage: builder (đọc apps.json secret) → backend
│                     Dùng khi cần custom apps trong production
│
└── layered/        ← Giống custom nhưng base image từ Docker Hub
                      Build nhanh hơn vì tận dụng pre-built layers
```

**Hiện tại** đang dùng image `frappe/erpnext:v16.23.0` (production image).

---

## 4. Hệ thống override (compose modular)

```
compose.yaml (core — không có DB, không có Redis)
     +
overrides/compose.mariadb.yaml      ← DB layer
     +
overrides/compose.redis.yaml        ← Cache/Queue layer
     +
overrides/compose.noproxy.yaml      ← Expose :8080 trực tiếp
  (hoặc compose.proxy.yaml)         ← Traefik HTTP
  (hoặc compose.https.yaml)         ← Traefik HTTPS + Let's Encrypt
     +
overrides/compose.backup-cron.yaml  ← Backup 6h/lần (Ofelia cron)
     +
overrides/compose.migrator.yaml     ← Auto migrate khi start
```

`docker-compose.local.yml` = tất cả phần trên gộp lại thành 1 file cho local dev.

---

## 5. Multi-tenancy model

```
                     frontend (nginx)
                          │
          ┌───────────────┼───────────────┐
          │               │               │
     site1.com        site2.com      site3.com
          │               │               │
          └───────────────┼───────────────┘
                          ▼
                    backend (1 process)
                          │
                    ┌─────┴─────┐
                 site1_db   site2_db   ← MariaDB (separate databases)
```

Nginx dùng `FRAPPE_SITE_NAME_HEADER` để route đúng site. Tất cả sites **share** cùng `sites/` volume và cùng backend process.

---

## 6. Volumes và data persistence

```
nexterp_sites            ← /home/frappe/frappe-bench/sites/
│                           common_site_config.json
│                           <sitename>/site_config.json
│                           <sitename>/private/files/
│                           <sitename>/public/files/
│
nexterp_db-data          ← MariaDB data files
nexterp_redis-queue-data ← Persistent job queue (tránh mất jobs khi restart)
nexterp_logs             ← Application logs
```

---

## 7. Frappe Framework concepts

Frappe dùng mô hình **DocType-driven development**:

```
DocType          ← Schema + UI + permissions (1 DocType = 1 table trong DB)
Controller       ← Python class (validate, on_submit, on_cancel hooks)
Hooks            ← app/hooks.py: wire events, schedulers, overrides
Fixtures         ← JSON data seeded vào DB khi install app
Form Scripts     ← Client-side JS (frappe.ui.form.on)
Jinja Templates  ← Print formats, email templates
REST API         ← /api/resource/{DocType} — tự động cho mọi DocType
Webhooks         ← push events ra ngoài khi document thay đổi
```

---

## 8. Điểm tích hợp (integration points)

| Phương thức | Endpoint | Dùng khi |
|---|---|---|
| REST API | `GET/POST /api/resource/{DocType}` | CRUD cơ bản |
| RPC | `POST /api/method/{app}.{module}.{function}` | Custom logic |
| Webhook | Config trong ERPNext UI | Push events ra hệ thống ngoài |
| Background jobs | `frappe.enqueue()` | Long-running tasks |
| Scheduler | `hooks.py → scheduler_events` | Cron tasks |
| Socket.IO | `:9000` | Realtime updates |

---

## 9. Workflow phát triển custom app

```
1. Tạo app mới trong devcontainer:
   bench new-app my_custom_app

2. Install vào site:
   bench --site frontend install-app my_custom_app

3. Thêm vào apps.json để build image:
   { "url": "https://github.com/myorg/my_custom_app", "branch": "main" }

4. Build custom image:
   docker build --secret=id=apps_json,src=apps.json \
     --file=images/layered/Containerfile --tag=myerpnext:1.0 .

5. Update docker-compose.local.yml:
   image: myerpnext:1.0
```

---

## 10. Bản đồ phát triển tiếp theo

Tùy vào mục tiêu, có 3 hướng chính:

**A. Tùy biến ERPNext (customize existing)**
→ Tạo custom app, override DocTypes, thêm fields, custom scripts
→ Dùng `devcontainer` + `bench new-app`

**B. Tích hợp hệ thống ngoài (integration)**
→ Dùng REST API `/api/resource/` hoặc `/api/method/`
→ Cấu hình Webhooks trong Settings → Webhooks
→ Dùng `frappe.enqueue()` cho async integration

**C. Mở rộng infrastructure**
→ Thêm backup tự động: `overrides/compose.backup-cron.yaml`
→ HTTPS với domain thật: `overrides/compose.https.yaml` + Traefik
→ Multi-site: thêm site qua `bench new-site`

# FinAgent Pro 生产部署清单

## 环境要求

- Python 3.10+
- Node.js 20+
- PostgreSQL 16+（生产数据库）
- Redis 7+（可选，用于分布式限流与缓存）
- Docker & Docker Compose（推荐部署方式）

## 关键环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://user:pass@db:5432/finagent_pro` |
| `REDIS_URL` | Redis 连接串（为空则禁用） | `redis://redis:6379/0` |
| `JWT_SECRET` | JWT 签名密钥（>=32 字节） | `your-256-bit-secret` |
| `ENV` | 运行环境 | `production` |
| `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` | LLM API 密钥 | `sk-...` |

## 推荐部署方式（Docker Compose）

```bash
cp .env.example .env
# 编辑 .env 填写密钥与数据库密码
docker compose up --build -d
```

验证：

```bash
curl http://localhost:8000/health
```

## 手动部署

### 后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 前端

```bash
cd frontend
npm install --legacy-peer-deps
npm run build
# 使用 nginx 托管 build/ 目录，参考 nginx.conf
```

## 发布前检查

- [ ] 后端：`python -m pytest -q`
- [ ] 后端：`ruff check backend/ --ignore=E501,F403,F405`
- [ ] 后端：`black --check backend/`
- [ ] 后端：`isort --check-only backend/`
- [ ] 前端：`npm run typecheck`
- [ ] 前端：`npm run lint`
- [ ] 前端：`npm run build`
- [ ] 前端：`npm run e2e`
- [ ] 压测：`python -m locust -f backend/locustfile.py --headless -u 50 -r 10 -t 30s --host http://127.0.0.1:8000`
- [ ] Docker：`docker compose config` 与 `docker compose build`

# Changelog

## [2.1.0] - 2026-06-18

### Added
- Playwright E2E 测试覆盖导航、主题切换、Agent 对话（支持本地系统 Chrome / CI 自动下载 Chromium）。
- GitHub Actions CI/CD：后端 SQLite 测试、前端 lint/typecheck/build、Playwright E2E、Docker 镜像构建与推送。
- Locust 压测脚本，覆盖 `/health`、`/openapi.json`、认证接口。
- 后端请求耗时/状态码日志中间件，提升生产环境可观测性。

### Changed
- 前端 echarts 改为按图表按需引入，配合路由级 `React.lazy` 代码分割；首屏 `index.js` 降至 205 KB（gzip 67 KB）。
- 后端测试默认使用 `sqlite+aiosqlite:///:memory:`，无需本地 PostgreSQL 即可跑完整测试。
- 全项目替换 `datetime.utcnow()` 为 timezone-aware UTC 时间戳。
- 生产环境隐藏 `/docs`、`/redoc`、`/openapi.json`。
- `/health` 在未配置 `REDIS_URL` 时跳过 Redis 检测，避免 2 秒超时等待。

### Fixed
- DAG 编排器并行步骤消息转发逻辑，确保测试断言通过。
- 前端 ESLint 未使用变量/导入警告。
- npm 依赖冲突（使用 `--legacy-peer-deps`）。
- 后端 `ruff`/`black`/`isort` 规范问题。

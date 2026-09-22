# 🛒 智能导购系统

基于 **Python(FastAPI) + Vue 3 + Element Plus + ECharts + SQLite + scikit-learn** 的「执行标准辅助智能导购」系统（课程设计 Demo）。

> 核心亮点：
> - **执行标准核验**：识别 GB/GB·T/QB·T 编号，核对现行/废止/未收录状态
> - **可解释推荐**：TF-IDF + 余弦相似度 + 多因素加权评分，给出推荐理由
> - **前后端解耦**：Vue 3 前端纯 HTTP 调用 FastAPI 契约服务（Swagger 文档）
> - **登录鉴权 + 邮箱注册**：JWT + PBKDF2 密码哈希；邮箱验证码注册/找回密码，收藏与历史按用户隔离
> - **安全防护**：发码/IP 限流、登录失败锁定、请求体大小限制、安全响应头
> - **Docker 部署**：nginx 前端 + uvicorn 后端一键编排

## 功能

| 页面 | 说明 |
| --- | --- |
| 🔐 登录/注册/找回密码 | 邮箱验证码注册、用户名或邮箱登录、忘记密码重置 |
| 🏠 首页 | 系统概览、指标卡与类别分布 |
| 🛍️ 商品中心 | 搜索/筛选商品，查看执行标准核验状态、收藏 |
| 🤖 智能导购 | 表单 + 一句话解析 → 标准核验 → 加权评分 → Top-N + 评分明细 |
| ⚖️ 商品对比 | 同类商品并排对比，指标最优高亮 |
| ❤️ 收藏商品 | SQLite 持久化收藏 |
| 🕘 推荐历史 | 历史查询与推荐结果回看 |
| 📊 数据分析 | 价格分布、品牌排行、评分-价格散点、标准合规统计 |

## 快速开始

### 本地开发

```bash
# 1) 后端
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export KESE_JWT_SECRET=$(python -c "import secrets;print(secrets.token_hex(32))")  # 可选，未设置则自动生成
python -m server.main              # http://localhost:8000/docs (Swagger)

# 2) 前端（另开终端）
cd web
npm install
npm run dev                        # http://localhost:5173 （已代理 /api → 8000）
```

> 打开前端后首次访问会跳转登录页。注册支持「邮箱验证码」：输入邮箱 → 点击发送验证码，
> 未配置 SMTP 时后端处于调试模式会在界面直接回显验证码（配置 SMTP 后走真实邮件）。
> 所有浏览器数据（收藏、历史）都按登录用户隔离。

### Docker 部署

```bash
export KESE_JWT_SECRET=$(openssl rand -hex 32)   # 生产环境务必设置强随机密钥
# 可选：配置邮箱验证码 SMTP（不配置则进入调试模式回显验证码）
export KESE_SMTP_HOST=smtp.example.com KESE_SMTP_PORT=465 KESE_SMTP_USER=you@example.com KESE_SMTP_PASSWORD=xxx
docker compose up --build -d
# 前端 http://localhost:8080 （nginx 托管并反代 /api）
# 后端 http://localhost:8000/docs （调试用）
# 数据（含用户/收藏/历史）持久化在命名卷 kese_data
```

## 技术架构

```
web/ (Vue 3 + Element Plus + ECharts 表现层，纯 HTTP 调用)
   ↓  /api/v1
server/ (FastAPI 契约层：schemas / app / service)
   ↓
services/ (业务层：推荐编排 / 标准核验 / 商品服务)
   ↓
algorithms/ (算法层：TF-IDF 余弦相似度 / 多因素加权评分)
   ↓
database/ + data/ (SQLite、种子 CSV、标准知识库 JSON)
```

统一数据模型 `Product` 屏蔽数据来源差异，后续接入真实电商爬虫只需新增 ProductSource Adapter。
前后端输出结构遵循 `docs/前后端契约.md`。

## 文档

- [docs/总体规划.md](docs/总体规划.md) — 定位、技术选型、架构、目录、里程碑
- [docs/模块详细设计.md](docs/模块详细设计.md) — 各模块职责与核心逻辑
- [docs/前后端契约.md](docs/前后端契约.md) — REST/JSON 契约（FastAPI 已落地）
- [docs/Demo实施说明.md](docs/Demo实施说明.md) — 运行步骤、演示脚本、答辩话术

# 智能导购系统 · Demo 实施说明

> 本 Demo 只完成一条「纵向」主链路，**不横向堆功能**：
>
> **Mock 商品数据 → 标准号提取/核验 → 多因素评分 → Top-N 推荐 → Vue 3 可视化展示**
>
> 前端为 Vue 3 + Element Plus，通过 HTTP 调用 FastAPI 契约服务；支持 Docker 部署。

---

## 1. Demo 范围

### 已完成（跑通）

1. **数据准备**：`data/products.csv` 44 条「食品接触类日用品」种子数据（保鲜盒/水杯/保温杯/餐具/奶瓶/电热水壶/玻璃杯/陶瓷餐具），经 `database/init_db.py` 灌入 SQLite。
2. **标准知识库**：`data/standards/standard_registry.json` 收录 12 条 GB/GB·T/QB·T 标准（含现行与废止状态，用日期版本区分替代关系）。
3. **标准核验**：`services/standard_service.py` 识别并核验商品执行标准编号，输出「现行 / 废止 / 未收录 / 未标注 / 无法识别」。
4. **智能推荐**：条件过滤 + TF-IDF 余弦相似度 + 7 维加权评分 + 可解释理由 + 评分明细。
5. **自然语言解析**：`core/text_process.py` 支持「150 以内 防漏耐高温的保鲜盒」→ 结构化字段，一键填充表单。
6. **页面（Vue 3）**：首页 / 商品中心 / 智能导购 / 商品对比 / 收藏 / 推荐历史 / 数据分析，全部通过 HTTP 契约接口取数。
7. **前后端契约实现**：`api_contract.py` + `server/`（FastAPI，含 Swagger 文档）；HTTP 引用推荐自动写入历史。
8. **Docker 部署**：`Dockerfile.api` + `Dockerfile.web`(nginx) + `docker-compose.yml`。

### 未做（刻意，后续迭代）

真实电商爬虫、OCR 包装识别、评论情感、跨平台 SKU 比价、多用户登录/鉴权。

---

## 2. 运行步骤

### 本地开发

```bash
cd kese01

# 1) 后端（自动建库 + 空库时导入种子数据）
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m server.main            # http://localhost:8000/docs

# 2) 前端（另开终端）
cd web
npm install
npm run dev                     # http://localhost:5173（已代理 /api → 8000）
```

### Docker 部署

```bash
docker compose up --build -d
# 前端：http://localhost:8080（nginx 托管 + 反代 /api）
# 后端：http://localhost:8000/docs（调试）
# 数据：命名卷 kese_data 持久化
```

---

## 3. 演示脚本（建议答辩顺序）

0. **登录/注册**：打开系统自动跳转登录页 → 点「立即注册」注册一个账号（自动登录）进入系统；演示退出登录、错误密码提示「用户名或密码错误」。
1. **首页**：展示商品/类别/标准核验占比指标 + 系统能力。
2. **商品中心**：搜索「手机」→ 无结果；搜索「保鲜盒」→ 展示执行标准核验状态（现行/废止/未标注）。
3. **智能导购**：
   - 表单方式：类别「保鲜盒」、预算 0~150、偏好「防漏、耐高温、食品级」→ 点「开始智能推荐」。
   - 演示结果：Top1 综合匹配度进度条、评分维度明细、执行标准核验「现行」、推荐理由列表。
   - 自然语言方式：展开「一句话描述需求」，输入 `150 以内 防漏耐高温的保鲜盒，品牌乐扣乐扣` → 解析出 JSON → 一键填充 → 推荐。
   - 勾选「仅看通过标准核验」→ 观察废止/未标注商品被过滤。
4. **商品对比**：类别「保温杯」→ 勾选 2~3 件 → 并排对比价格/评分/标准状态，指标最优高亮 🏆。
5. **收藏 & 历史**：从推荐结果收藏商品 → 查看收藏；回看推荐历史与当时查询条件。
6. **数据分析**：价格分布、品牌排行、评分-价格散点、标准核验分布饼图。

---

## 4. 答辩话术要点

### Q：你的「智能」体现在哪里？

> 系统先把商品特征与用户需求做文本向量化（TF-IDF），用余弦相似度度量需求匹配度；
> 再结合执行标准核验、价格匹配、评分、销量、品牌、店铺信誉等 7 个因素加权评分，
> 排序后生成 Top-N 个性化推荐，并**给出每一条推荐的可解释理由**。

### Q：执行标准核验是怎么回事？

> 商品详情里往往只写「执行标准：GB4806.7」等编号。系统先归一化编号（去空格/统一年份/统一分隔符），
> 再到本地标准知识库核验：是否存在、现行还是废止、适用范围。核验结论（现行=100，废止=10）作为推荐评分的 20% 权重。

### Q：数据从哪来？会不会是假数据？

> Demo 阶段使用 `MockProductSource`（CSV → SQLite）跑通全链路。因为架构上采用了
> 「ProductSource 适配器 + 统一 Product 模型」，以后接入京东/淘宝爬虫、Pinduoduo 官方 API 时，
> 推荐与核验逻辑一行都不用改，只需新增一个 Adapter 实现同一导入接口。

### Q：登录鉴权是怎么做的？

> 采用 JWT（JSON Web Token）Bearer 认证：用户密码用 PBKDF2-HMAC-SHA256（20 万次迭代 + 随机盐）哈希后存 SQLite，
> 登录成功后签发带 7 天有效期的 HS256 令牌；前端把令牌存本地并在每次请求自动注入 `Authorization` 头。
> 除健康检查/注册/登录外，其余接口都要鉴权，收藏和历史按用户 ID 隔离，互不可见。前端收到 401 自动清空登录态并跳转登录页。

---

## 5. 关键文件速查

| 想看什么 | 文件 |
| --- | --- |
| 前端入口/路由 | `web/src/App.vue`、`web/src/router.js` |
| 前端登录态 | `web/src/auth.js`、`web/src/store.js`、`web/src/views/LoginView.vue` |
| 前端 API 客户端 | `web/src/api.js` |
| 前端页面 | `web/src/views/*` |
| 契约 Schema | `server/schemas.py` |
| 契约路由 | `server/app.py` |
| 认证安全 | `server/security.py` |
| 数据访问（含用户隔离） | `database/db.py` |
| 推荐主链路 | `services/recommendation_service.py` |
| 标准核验 | `services/standard_service.py` |
| 相似度算法 | `algorithms/similarity.py` |
| 评分引擎 | `algorithms/scoring.py` |
| 自然语言解析 | `core/text_process.py` |
| 数据模型 | `core/models.py` |
| SQLite 访问 | `database/db.py` |
| 种子数据 | `data/products.csv` |
| 标准知识库 | `data/standards/standard_registry.json` |

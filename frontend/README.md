# JobPilot AI 前端

第一版 MVP 覆盖岗位、简历、匹配报告、学习计划和工作台，通过真实
`/api/v1` HTTP 接口连接 FastAPI，不包含知识库、问答、Agent 和用户认证。

开发时先在项目根目录启动 FastAPI，再启动前端：

```powershell
npm run dev
```

Vite 会把 `/api` 请求代理到 `http://127.0.0.1:8000`。也可以通过
`VITE_API_BASE_URL` 指定其他 API 地址。

验证命令：

```powershell
npm run lint
npm run build
```

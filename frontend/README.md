# RepoMentor 前端

RepoMentor 前端使用 React + Vite 构建，提供两个页面：

- 用户页：面向新贡献者，展示仓库概览、代码地图、学习路径、开发流程、推荐任务和仓库问答。
- 调试页：面向开发者和评审，展示 Agent Flow、Worker 输出、Data Layer、Shared Memory、SelfCheck、FinalAnswer JSON 和模型状态。

## 本地启动

```powershell
cd frontend
npm install
npm run dev
```

默认访问地址：

```text
http://127.0.0.1:5173
```

## 后端地址配置

前端通过 `VITE_API_BASE_URL` 读取后端地址。

```powershell
copy .env.example .env
```

本地默认配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 构建检查

```powershell
npm run build
```

当前仓库暂不包含公网发布配置，公开提交中只保留本地开发运行说明。

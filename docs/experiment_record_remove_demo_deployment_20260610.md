# 实验记录：移除 Demo 与部署交付内容

## 时间

2026-06-10

## 目标

根据展示阶段的新要求，公开仓库暂时不再提供在线部署、Docker 一键部署、录屏 Demo 脚本或提交地址占位模板。仓库保留核心代码、本地运行方式、PPT 展示材料、设计依据、测试总结和完整交互轨迹。

同时将 README 统一为中文，避免公开仓库中出现中英混杂、乱码文案或未完成的部署承诺。

## 修改范围

- 删除部署与 Demo 相关文件：
  - `docker-compose.yml`
  - `render.yaml`
  - `backend/Dockerfile`
  - `backend/.dockerignore`
  - `backend/start.sh`
  - `frontend/Dockerfile`
  - `frontend/.dockerignore`
  - `frontend/vercel.json`
  - `scripts/check_deployment.py`
  - `docs/demo_script.md`
  - `docs/deployment_guide.md`
  - `docs/submission_checklist.md`
  - `docs/submission_urls.md`
  - `presentation/demo_script.md`
  - `presentation/submission_checklist.md`
  - `presentation/assets/demo_user_annotated.png`
  - `presentation/assets/demo_debug_annotated.png`
- 更新中文 README：
  - `README.md`
  - `frontend/README.md`
  - `backend/README.md`

## 验证计划

- 检查 Git 状态，确认删除和 README 修改都在本次提交范围内。
- 搜索 README，确认不再包含在线部署占位地址、Docker 一键 Demo 或 Vercel/Render 提交说明。
- 保留本地运行入口：后端 `8000`，前端 `5173`。

## 已知取舍

- PPT/PDF 已重命名为 `RepoMentor_Final_Presentation.pptx` 和 `RepoMentor_Final_Presentation.pdf`。
- 代码仍可本地运行，但仓库不再承诺在线部署或 Docker 一键运行。

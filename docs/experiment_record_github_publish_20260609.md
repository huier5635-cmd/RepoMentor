# 实验记录：GitHub 开源发布准备

## 时间

2026-06-09

## 目标

将 RepoMentor 整理成可公开发布的 GitHub 开源项目，并增强 README 的传播入口。

## 改动

- README 增加开源项目首屏、亮点、截图、快速运行、展示材料和 Star 引导。
- 新增 `LICENSE`。
- 新增 `CONTRIBUTING.md`。
- 新增 `SECURITY.md`。
- `.gitignore` 排除提交包、缓存、构建产物、日志和敏感环境文件。

## 安全检查

- 使用 `rg` 扫描真实 API Key / GitHub Token / 私钥形态。
- `.env`、缓存目录、node_modules、submission package zip 不进入 git。

## 当前限制

- 本机没有 GitHub CLI。
- GitHub Connector 已登录 `huier5635-cmd`，但当前工具没有创建新仓库接口。
- 若远程仓库不存在，需要先在 GitHub 网页创建空仓库，再添加 remote 并 push。

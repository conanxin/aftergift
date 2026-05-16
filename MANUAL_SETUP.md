# 手动创建 GitHub 仓库

由于 `gh` CLI 不可用，请手动创建仓库：

## 方法 1：GitHub 网页（推荐）

1. 打开 https://github.com/new
2. Repository name: `aftergift`
3. Description: "Aftergift / 后来礼物 — 关系旧物的温柔流转平台原型"
4. 选择 Public
5. 不要勾选 "Add a README file"（已有）
6. 点击 "Create repository"

## 方法 2：GitHub API（需 Personal Access Token）

```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -d '{"name":"aftergift","description":"Aftergift / 后来礼物 — 关系旧物的温柔流转平台原型","public":true}' \
  https://api.github.com/user/repos
```

## 推送已初始化的仓库

创建仓库后，执行：

```bash
cd ~/projects/aftergift
git remote set-url origin git@github.com:conanxin/aftergift.git
git branch -M main
git push -u origin main
```

## 当前仓库状态

- 已初始化 Git 仓库
- 已 commit（初始提交）
- Remote 已设置：`git@github.com:conanxin/aftergift.git`
- 等待 GitHub 仓库创建后 push

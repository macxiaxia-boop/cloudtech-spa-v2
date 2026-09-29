#!/bin/bash
# CloudTech release-v2.0.0 · 推送到 remote 脚本
# 用法：bash scripts/push-to-remote.sh <remote-url>
# 示例：bash scripts/push-to-remote.sh https://github.com/myorg/CloudTech-Portable.git

set -e

REMOTE_URL=${1:-""}

if [ -z "$REMOTE_URL" ]; then
  echo "❌ 用法：bash $0 <remote-url>"
  echo "   示例：bash $0 https://github.com/myorg/CloudTech-Portable.git"
  exit 1
fi

echo "🚀 CloudTech release-v2.0.0 推送脚本"
echo "   Remote: $REMOTE_URL"
echo

# 1. 检查 git status
echo "📊 [1/5] 检查 git status ..."
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ 工作区有未提交修改，请先 commit"
  git status --short
  exit 1
fi
echo "✅ 工作区干净"

# 2. 检查当前分支
echo "📊 [2/5] 检查当前分支 ..."
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "master" ]; then
  echo "⚠️  当前不在 master 分支（$CURRENT_BRANCH），将推送 master"
fi
echo "✅ 当前分支：$CURRENT_BRANCH"

# 3. 检查 tags
echo "📊 [3/5] 检查 tags ..."
RELEASE_TAG=$(git tag --list "release-v2.0.0")
if [ -z "$RELEASE_TAG" ]; then
  echo "❌ release-v2.0.0 tag 不存在"
  exit 1
fi
echo "✅ Release tag: $RELEASE_TAG"

# 4. 配置 remote
echo "📊 [4/5] 配置 remote ..."
if git remote | grep -q "^origin$"; then
  CURRENT_REMOTE=$(git remote get-url origin)
  if [ "$CURRENT_REMOTE" != "$REMOTE_URL" ]; then
    echo "⚠️  当前 origin: $CURRENT_REMOTE"
    echo "   新 origin: $REMOTE_URL"
    echo "   替换中..."
    git remote set-url origin "$REMOTE_URL"
  else
    echo "✅ origin 已配置: $REMOTE_URL"
  fi
else
  git remote add origin "$REMOTE_URL"
  echo "✅ 添加 origin: $REMOTE_URL"
fi

# 5. 推送 master + tags
echo "📊 [5/5] 推送 master + tags ..."
echo "   推送 master（17 commits）..."
git push -u origin master

echo "   推送 tags ..."
git push origin --tags

echo
echo "🎉 推送完成！"
echo "   Repository: $REMOTE_URL"
echo "   Latest commit: $(git rev-parse HEAD | cut -c1-7)"
echo "   Release tag: $RELEASE_TAG"
echo
echo "📋 推送后自动触发："
echo "   - GitHub Actions: .github/workflows/lighthouse-ci.yml"
echo "   - Lighthouse 报告自动生成"
echo "   - Bundle size check 自动跑"
echo
echo "🚀 部署到生产（任选）："
echo "   Vercel:  cd web/vite-spa && vercel --prod"
echo "   Docker:  docker build -t cloudtech-spa:v2.0.0 . && docker run -p 80:80 cloudtech-spa:v2.0.0"

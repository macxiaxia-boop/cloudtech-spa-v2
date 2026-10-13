#!/bin/bash
# CloudTech V4 — Production Ready 一键脚本 (Linux/macOS/Git Bash)
# 在能访问 github.com + 媒体 API + Postgres 的机器上跑
# 红线 #60: 不替你假装完成 — 所有步骤都需你显式确认

set -e

echo "============================================================"
echo "CloudTech V4 — Production Ready"
echo "============================================================"

# Step 1: 检查本地 commit 状态
echo
echo "[1/7] 检查本地 commit 状态"
git log --oneline -3
echo

# Step 2: 推送 remote
echo "[2/7] 推送 remote (github.com)"
read -p "确认推送? (yes/no): " push_confirm
if [[ "$push_confirm" == "yes" ]]; then
  git push origin master
  echo
fi

# Step 3: 设置 env vars
echo "[3/7] 设置 env vars"
echo "需要: V4_JWT_SECRET / DOUBAO_API_KEY / TIKHUB_TOKEN / DATABASE_URL"
echo "如已有, 跳过此步"
echo

# Step 4: 跑 Postgres migration
echo "[4/7] 跑 Postgres migration (L5 不可逆, 需你确认)"
read -p "确认跑真实 DB migration? (yes/no): " db_confirm
if [[ "$db_confirm" == "yes" ]]; then
  python scripts/run_v4_migration.py --execute
  echo
fi

# Step 5: 跑全部 V4 测试
echo "[5/7] 跑全部 V4 测试"
python -m pytest tests/test_v4_*.py tests/test_adapters_*.py tests/test_workbuddy_*.py tests/test_real_provider_clients.py -q
echo

# Step 6: 写真实 doubao 调用
echo "[6/7] 启真实 doubao_seedream (需 __enable_real=True)"
read -p "启真实 doubao? (yes/no): " real_doubao
if [[ "$real_doubao" == "yes" ]]; then
  read -p "DOUBAO_API_KEY: " -s DOUBAO_KEY
  export DOUBAO_API_KEY
  python -c "
import os
from adapters.media.real_providers import get_real_client
from adapters.media.types import MediaRequest
r = get_real_client('doubao_seedream')._call(
    MediaRequest(operation='image.generate',
                inputs={'prompt': 'test 现代简约客厅', '__enable_real': True},
                tenant_id='t_test_v4_001', idempotency_key='k_test_001',
                estimated_cost_cents=20, cost_class='METERED_MEDIA'),
    'token')
print('real result:', r.mock, r.output_assets[0].get('url'))
"
  echo
fi

# Step 7: 启动 FastAPI 服务
echo "[7/7] 启动 FastAPI 服务"
echo "uvicorn api.v4:app --host 0.0.0.0 --port 8000"
echo "然后 vite-spa 调用 /v4/*"

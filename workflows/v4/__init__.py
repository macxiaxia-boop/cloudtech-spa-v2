"""CloudTech V4 — 横向工作路径基础设施
不重写 workflows/base.py; 在 base 之上扩展:
  * 7 类 node_kinds
  * 状态机扩展 (BLOCKED_PERMISSION/BLOCKED_BUDGET/RETRY_WAIT/PARTIAL)
  * typed contract 校验
  * 媒体门禁 (server-side allow/deny, 不依赖 prompt)
  * 预算预占 + 幂等键
  * 资产别名解析
"""
from .node_kinds import NodeKind, NODE_KINDS
from .orchestrator import V4Orchestrator, RunStatus, RunStatusError
from .registry import OperationRegistry, OperationDefinition
from .budget import BudgetGate, CostClass, BudgetError
from .media_gate import MediaGate, MediaGateError
from .idempotency import IdempotencyStore, IdempotencyHit
from .asset_resolver import AssetResolver, AssetBindingError

__all__ = [
    "NodeKind", "NODE_KINDS",
    "V4Orchestrator", "RunStatus", "RunStatusError",
    "OperationRegistry", "OperationDefinition",
    "BudgetGate", "CostClass",
    "MediaGate", "MediaGateError",
    "IdempotencyStore", "IdempotencyHit",
    "AssetResolver", "AssetBindingError",
]

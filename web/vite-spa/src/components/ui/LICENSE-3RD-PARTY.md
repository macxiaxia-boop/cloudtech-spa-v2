# 3RD-PARTY LICENSE · shadcn/ui 组件库

> **来源**: https://github.com/shadcn-ui/ui
> **Commit SHA**: `db2db460a26fa84fb65c8d903b213925fbdee9ed` (2026-09-28)
> **License**: MIT — Copyright (c) 2023 shadcn
> **本地路径**: `src/components/ui/*.tsx` （共 61 文件）

## 使用条款

本目录下的 React 组件源码复制自 shadcn/ui v4 registry（new-york-v4 风格），遵循 MIT 许可证，允许：

- ✅ 商用
- ✅ 修改
- ✅ 分发
- ✅ 私有使用

唯一义务：**保留版权声明和许可声明**（即本文件 + 每个源文件顶部 SPDX 头）。

## CloudTech 改造清单

| 改造项 | 范围 |
|---|---|
| `cn` import 路径 | `from "cn"` → `from "@/lib/utils"`（已批量修复） |
| 主题色覆盖 | 通过 globals.css CSS 变量驱动；无需逐文件改 |
| 图标 | 默认 lucide-react（与 CloudTech 现有依赖一致） |
| dark 变体 | 暂保留（暂留 light only，dark hook 预留） |

## 完整 License 原文

```
MIT License

Copyright (c) 2023 shadcn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 同步引用

- 设计系统: `design/research/deliverables/CLOUDTECH_DESIGN_SYSTEM.md`
- 借鉴映射: `design/research/deliverables/REFERENCE_SOURCE_MAP.csv`
- 实施计划: `design/research/deliverables/UI_IMPLEMENTATION_PLAN.md`
- 视觉母版: `design/research/screenshots/visual-master-20260929.png` (SHA256 `5d6f1e40...`)

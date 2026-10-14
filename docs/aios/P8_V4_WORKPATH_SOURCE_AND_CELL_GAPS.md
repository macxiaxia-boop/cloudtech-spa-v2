# P8 CloudTech 六条已存在的 V4 工作路径——源码细胞与施工入口

> 2026-10-14；本文件是工程溯源与最小施工映射，不是另建 Workflow 框架。不得据此假称所有 Provider 真正已接入。

## 现有路由唯一事实源

路径定义：`workflows/v4/paths.py`；执行状态：`workflows/v4/orchestrator.py`；操作入口：`workflows/v4/registry.py`；节点种类 `workflows/v4/node_kinds.py`；下面的 V4 名称和 ID 均来自已有代码：

| 原路径（不能替代或重命名） | 细胞操作顺序 | 需打通的实际运行节点 |
|---|---|---|
| `WP-BLOGGER-RESEARCH` | `url.normalize → platform.permission_check → platform.homepage_parse → content.dedupe → transcript.extract → content.structure.analyze → content.original_script.generate → content.similarity.review → content.storyboard.generate → doubao.tts → export.zip` | 主页真实采集、权限、字幕、原创脚本、审查、输出 |
| `WP-VIDEO-TRANSCRIBE` | `video.ingest → transcript.extract + video.frame_extract → content.structure.analyze → content.original_script.generate → content.similarity.review` | 自有视频输入与真实 ASR、视频帧、原创 |
| `WP-ARTICLE-REWRITE` | `platform.access_check → article.html_parse → article.media_extract + content.research → content.license_check + content.outline.generate → content.rewrite → content.similarity.review` | 图文段落顺序、配图授权与草稿 |
| `WP-RENOVATION-FULL` | `asset.role.bind → vision.analyze → renovation.style_plan → renovation.room_card → budget.estimate → image.reference_fusion → image.quality_check → export.gallery` | 户型/风格/家具图角色、真实生图、局部替换与保真检查 |
| `WP-GROWTH-VIDEO` | `video.frames_validate → video.storyboard → budget.estimate → video.image_to_video x2 → video.stitch_ffmpeg → video.quality_check → export.video` | 真实生成分段、15秒时长、音画同步与输出哈希 |
| `WP-PRODUCT-MARKETING` | `vision.product_verify → product.scene_plan → image.crop_or_outpaint + video.script.generate → video.generate + doubao.tts + content.adapt_platform → content.compliance_check → export.package` | 商品保真、多平台图、视频、合规、打包 |

## 静态发现的实际缺口，不允许用 mock 伪装已完工

1. `adapters/platform/homepage_parser.py` 目前返回 `retrieved_policy=mock` 的模拟作品和字典 `items`，不是线上平台授权采集。P8 修复了 registry 曾把这个 dict 当列表切片的契约问题，但结果仍为 `ok=False, status=MOCK_HOMEPAGE_NOT_VERIFIED`。
2. `adapters/platform/permission_gate.py` 使用 mock 规则，`allowed=True` 只表示规则 hint，不代表用户账号/OAuth权限。P8 结果为 `permission_verified=False`。
3. `adapters/transcribe/asr_engine.py` 为固定样例字幕，`adapters/content/original_script_generator.py` 声明 mock-only；结构拆解无 Provider 时有启发式 mock 分支。必须绑定真实合法 Provider 才能升到真实内容生产。
4. `adapters/media/provider_registry.py` 包含 mock-stub，多数生图/生视频节点未提供真实账单和输出证据。
5. `workflows/v4/registry.py` 对未知操作不能返回一个看似成功的 `stub`；P8 改为 `UNREGISTERED_OPERATION` 并将模拟 ZIP 标为 `MOCK_EXPORT_NOT_AN_ARTIFACT`。
6. 原 registry 对 `adapters.ocr` 等插件做了顶层 eager import，导致即使只调用 `url.normalize` 也会因为缺少不相关依赖失败。P8 改成每个 operation 按需 import，缺失的 OCR/LLM/meeting 单独维持 GAP，而不伪造适配器。
7. 前端另有 `web/vite-spa/src/App.tsx` 对 `./pages/lynxce/index` 的引用无法被当前源树解析。必须追溯原始页面资产，不能创建空白替身刷 CI。

## 每个操作怎样被 AIOS 接管

请求时至少：`tenant_id, actor_id, run_id, path_id, node_id, input_refs, permission_scope, budget_limit`。

执行前按 `WorkPathDefinition.steps` 完整拓扑检查；`OperationRegistry.dispatch` 仅能路由到真实注册 adapter，`mock/stub/未注册` 不得记为执行成功。媒体生成需预算和供应商额度门禁，外部发帖需人工内容哈希审批。

若有外部副作用：AIOS P7 `effect_key = SHA256(run_id:node_id)`，执行前持久记录 PREPARED→SENT；远端资源回执未验证记为 UNVERIFIED，超时记 UNCERTAIN；必须由独立只读 Verifier 检查租户账户/平台资源 ID 才能 CONFIRMED。不能仅凭 `ok: true` 或 `resource_id` 宣布业务完成。

每个节点回写：`node_id, input_hash, output_ref, provider_req_id, provider, cost, error_code, retry_class, trace_id, sha256, test_evidence`。跨节点只传 typed refs，不传不可校验的大段模糊自然语言。

## 真正工程顺序

`P8-V4-A01` 为六条 V4 各 50 个已定义节点逐项建立 operation→adapter 清单，`B01` 修返回契约和 stub误成功，`C01` 对转录、主页采集、媒体生成分别接有授权真实Provider，`D01` 打通 AIOS 工作流运行和独立验证，`E01` 扩到另外 24 条 P8 候选业务路线与 73 分组、3920 源 ID。

每个阶段都要引用真实 CI 日志、源码 SHA、业务输入输出和故障反例。P8 的 30 条业务路径只是研究施工视图，绝对不可覆盖此处六条 V4 原路径。

## 关联

AIOS 源仓库：`macxiaxia-boop/aios-sovereignty-v` Draft PR #3。CloudTech 本仓库：Draft PR #1。二者 PR 均不得在缺少独立验证与用户批准时自动合并、对外发布或上生产。

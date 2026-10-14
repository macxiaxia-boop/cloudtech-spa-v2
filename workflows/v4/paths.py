"""V4 — 6 类旗舰工作路径定义
对应 V4 spec §06:
  A. 博主主页研究 → 原创系列 (WP009→010→011→019→024→025→027)
  B. 单视频 → 提取原文 → 仿写原创 (WP012→013→019)
  C. 图文链接 → 原文+配图 → 二创 (WP016→020)
  D. 多参考图 → 全屋效果图 → 局部替换 (WP001→002)
  E. 毛坯+完成图 → 15秒视频 (WP004)
  F. 商品源图 → 图文营销全套 (WP006→007→032→040)
"""
from __future__ import annotations
from .contract import WorkPathDefinition, StepSpec, InputSpec


def _to_steps(steps):
    return [StepSpec(**s) if isinstance(s, dict) else s for s in steps]


# === A. 博主主页研究 → 原创系列 (WP009→010→011→019→024→025→027) ===
WP_BLOGGER_RESEARCH = WorkPathDefinition(
    id="WP-BLOGGER-RESEARCH",
    revision=1,
    title="博主主页研究 → 原创系列",
    domain="creator",
    goal="从公开博主主页 URL 提取作品列表 → 内容特征研究 → 选题分析 → 行业适配 → 原创脚本 → 配音 → 剪辑",
    triggers=["用户粘贴主页 URL", "用户要求研究博主风格", "用户要求生成原创选题"],
    preconditions=["URL 可公开访问", "平台允许抓取公开元数据"],
    inputs=[
        InputSpec(role="homepage_url", mime="text/url", min=1, max=1),
        InputSpec(role="target_industry", mime="text/plain", min=1, max=1),
        InputSpec(role="audience", mime="text/plain", min=0, max=1),
    ],
    planner="intent_resolver_v4",
    steps=[
        {"id": "url_normalize", "operation": "url.normalize", "node_kind": "TRANSFORM", "cost_class": "FREE_LOCAL"},
        {"id": "permission_check", "operation": "platform.permission_check", "node_kind": "FETCH_PUBLIC", "cost_class": "METERED_NONMEDIA"},
        {"id": "homepage_parse", "operation": "platform.homepage_parse", "requires": ["url_normalize"], "node_kind": "FETCH_PUBLIC", "cost_class": "METERED_NONMEDIA"},
        {"id": "work_list_dedupe", "operation": "content.dedupe", "requires": ["homepage_parse"], "node_kind": "TRANSFORM", "cost_class": "FREE_LOCAL"},
        {"id": "transcript_extract", "operation": "transcript.extract", "requires": ["work_list_dedupe"], "node_kind": "TRANSFORM", "cost_class": "METERED_NONMEDIA", "retries": 2},
        {"id": "structure_analyze", "operation": "content.structure.analyze", "requires": ["transcript_extract"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "topic_ideas", "operation": "content.original_script.generate", "requires": ["structure_analyze"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "similarity_qc", "operation": "content.similarity.review", "requires": ["topic_ideas"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA", "checkpoint": "human_review_topics"},
        {"id": "storyboard", "operation": "content.storyboard.generate", "requires": ["topic_ideas"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "tts", "operation": "doubao.tts", "requires": ["storyboard"], "node_kind": "MEDIA_GENERATE", "cost_class": "METERED_NONMEDIA", "checkpoint": "budget_approve_tts"},
        {"id": "export", "operation": "export.zip", "requires": ["similarity_qc", "storyboard", "tts"], "node_kind": "EXPORT", "cost_class": "FREE_LOCAL"},
    ],
    quality_gates=["similarity_score<0.35", "all_topics_have_evidence", "rights_status != unknown"],
    exported_artifacts=["topic_cards", "script_files", "tts_audio", "provenance_manifest"],
    recovery={"retry_failed_only": True, "resume_from_node_id": True, "no_repeat_billing": True},
    privacy="public_with_attribution",
    permissions=["public_metadata_only"],
    billing_policy="MIXED",
    evidence={"source_urls": True, "transcript_timestamp": True, "similarity_score": True},
)


# === B. 单视频 → 提取原文 → 仿写原创 (WP012→013→019) ===
WP_VIDEO_TRANSCRIBE = WorkPathDefinition(
    id="WP-VIDEO-TRANSCRIBE",
    revision=1,
    title="单视频转写 → 仿写原创",
    domain="extraction",
    goal="合法视频链接/自有视频文件 → 原文逐字稿 → 结构解剖 → 原创脚本",
    triggers=["用户提供视频 URL/file", "用户要求提取口播稿", "用户要求仿写视频"],
    preconditions=["视频可访问/自有", "用户授权提取"],
    inputs=[
        InputSpec(role="video_source", mime="video/file+url", min=1, max=1),
        InputSpec(role="target_industry", mime="text/plain", min=0, max=1),
    ],
    planner="intent_resolver_v4",
    steps=[
        {"id": "ingest", "operation": "video.ingest", "node_kind": "FETCH_PUBLIC", "cost_class": "METERED_NONMEDIA"},
        {"id": "asr", "operation": "transcript.extract", "requires": ["ingest"], "node_kind": "TRANSFORM", "cost_class": "METERED_NONMEDIA"},
        {"id": "frame_extract", "operation": "video.frame_extract", "requires": ["ingest"], "node_kind": "TRANSFORM", "cost_class": "FREE_LOCAL"},
        {"id": "structure", "operation": "content.structure.analyze", "requires": ["asr", "frame_extract"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "original_script", "operation": "content.original_script.generate", "requires": ["structure"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "qc", "operation": "content.similarity.review", "requires": ["original_script"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
    ],
    quality_gates=["asr_word_count>0", "similarity<0.35"],
    exported_artifacts=["transcript_srt", "transcript_txt", "original_script", "qc_report"],
    recovery={"retry_failed_only": True},
    privacy="derived",
    permissions=["self_or_authorized"],
    billing_policy="METERED_NONMEDIA",
    evidence={"asr_engine": True, "source_hash": True},
)


# === C. 图文链接 → 原文+配图 → 二创 (WP016→020) ===
WP_ARTICLE_REWRITE = WorkPathDefinition(
    id="WP-ARTICLE-REWRITE",
    revision=1,
    title="图文链接 → 原文+配图 → 原创改写",
    domain="extraction",
    goal="公开图文链接 → 原文+授权图片 → 原创平台笔记",
    triggers=["用户粘贴图文 URL", "用户要求提取原文", "用户要求二创"],
    preconditions=["链接可访问", "授权判断通过"],
    inputs=[InputSpec(role="article_url", mime="text/url", min=1, max=1)],
    planner="intent_resolver_v4",
    steps=[
        {"id": "access_check", "operation": "platform.access_check", "node_kind": "FETCH_PUBLIC", "cost_class": "METERED_NONMEDIA"},
        {"id": "html_parse", "operation": "article.html_parse", "requires": ["access_check"], "node_kind": "FETCH_PUBLIC", "cost_class": "METERED_NONMEDIA"},
        {"id": "media_extract", "operation": "article.media_extract", "requires": ["html_parse"], "node_kind": "FETCH_PUBLIC", "cost_class": "METERED_NONMEDIA"},
        {"id": "license_check", "operation": "content.license_check", "requires": ["media_extract"], "node_kind": "TRANSFORM", "cost_class": "FREE_LOCAL"},
        {"id": "research", "operation": "content.research", "requires": ["html_parse"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "outline", "operation": "content.outline.generate", "requires": ["research"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "rewrite", "operation": "content.rewrite", "requires": ["outline", "license_check"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "qc", "operation": "content.similarity.review", "requires": ["rewrite"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
    ],
    quality_gates=["similarity<0.30", "all_images_have_license", "facts_verified"],
    exported_artifacts=["original_article", "licensed_images", "provenance"],
    recovery={"retry_failed_only": True},
    privacy="derived",
    permissions=["public_only"],
    billing_policy="METERED_NONMEDIA",
    evidence={"source_url": True, "license_per_image": True},
)


# === D. 多参考图 → 全屋效果图 → 局部替换 (WP001→002) ===
WP_RENOVATION_FULL = WorkPathDefinition(
    id="WP-RENOVATION-FULL",
    revision=1,
    title="多参考图 → 全屋效果图 → 局部替换",
    domain="creation",
    goal="图 1 户型 + 图 2 风格 + 图 3-图 N 家具 + 文字 → 全屋风格总纲 + 空间卡 + 批量效果图 + 局部换物",
    triggers=["用户上传多张参考图", "用户要求装修效果图", "用户要求换家具"],
    preconditions=["图角色已绑定 (户型/风格/家具/要求)"],
    inputs=[
        InputSpec(role="floorplan_image", mime="image/*", min=1, max=1),
        InputSpec(role="style_reference", mime="image/*", min=1, max=1),
        InputSpec(role="furniture_refs", mime="image/*", min=0, max=10),
        InputSpec(role="requirements_text", mime="text/plain", min=0, max=1),
    ],
    planner="intent_resolver_v4",
    steps=[
        {"id": "asset_bind", "operation": "asset.role.bind", "node_kind": "TRANSFORM", "cost_class": "FREE_LOCAL"},
        {"id": "vision_analysis", "operation": "vision.analyze", "requires": ["asset_bind"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONIA"},
        {"id": "style_plan", "operation": "renovation.style_plan", "requires": ["vision_analysis"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "room_card", "operation": "renovation.room_card", "requires": ["style_plan"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "budget_estimate", "operation": "budget.estimate", "requires": ["room_card"], "node_kind": "TRANSFORM", "cost_class": "FREE_LOCAL", "checkpoint": "budget_approve_media"},
        {"id": "image_generate", "operation": "image.reference_fusion", "requires": ["budget_estimate", "room_card"], "node_kind": "MEDIA_GENERATE", "cost_class": "METERED_MEDIA", "retries": 2},
        {"id": "qc", "operation": "image.quality_check", "requires": ["image_generate"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "export", "operation": "export.gallery", "requires": ["qc"], "node_kind": "EXPORT", "cost_class": "FREE_LOCAL"},
    ],
    quality_gates=["all_rooms_have_images", "version_id_per_alias"],
    exported_artifacts=["style_doc", "room_cards", "image_zip", "manifest"],
    recovery={"retry_failed_only": True, "alias_version_lock": True},
    privacy="private_to_tenant",
    permissions=["own_or_authorized_media"],
    billing_policy="METERED_MEDIA",
    evidence={"provider_name": True, "model_id": True, "cost_per_image": True},
)


# === E. 毛坯+完成图 → 15秒视频 (WP004) ===
WP_GROWTH_VIDEO = WorkPathDefinition(
    id="WP-GROWTH-VIDEO",
    revision=1,
    title="毛坯+完成图 → 15秒生长视频",
    domain="creation",
    goal="首帧(毛坯) + 尾帧(成品) → 镜头方案 → 分段视频生成 → 拼接成约 15 秒视频",
    triggers=["用户提供首尾帧对", "用户要求生长视频"],
    preconditions=["首尾帧尺寸兼容", "时长 ≤ provider_max_segment × N"],
    inputs=[
        InputSpec(role="first_frame", mime="image/*", min=1, max=1),
        InputSpec(role="last_frame", mime="image/*", min=1, max=1),
        InputSpec(role="duration_sec", mime="number", min=0, max=1),
    ],
    planner="intent_resolver_v4",
    steps=[
        {"id": "frames_validate", "operation": "video.frames_validate", "node_kind": "TRANSFORM", "cost_class": "FREE_LOCAL"},
        {"id": "storyboard", "operation": "video.storyboard", "requires": ["frames_validate"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "budget_estimate", "operation": "budget.estimate", "requires": ["storyboard"], "node_kind": "TRANSFORM", "cost_class": "FREE_LOCAL", "checkpoint": "budget_approve_media"},
        {"id": "video_segment_1", "operation": "video.image_to_video", "requires": ["budget_estimate"], "node_kind": "MEDIA_GENERATE", "cost_class": "METERED_MEDIA"},
        {"id": "video_segment_2", "operation": "video.image_to_video", "requires": ["budget_estimate"], "node_kind": "MEDIA_GENERATE", "cost_class": "METERED_MEDIA"},
        {"id": "stitch", "operation": "video.stitch_ffmpeg", "requires": ["video_segment_1", "video_segment_2"], "node_kind": "TRANSFORM", "cost_class": "FREE_LOCAL"},
        {"id": "qc", "operation": "video.quality_check", "requires": ["stitch"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "export", "operation": "export.video", "requires": ["qc"], "node_kind": "EXPORT", "cost_class": "FREE_LOCAL"},
    ],
    quality_gates=["final_duration_in_14_16", "no_synthetic_filling"],
    exported_artifacts=["final_video", "storyboard_doc", "segment_urls"],
    recovery={"retry_failed_only": True},
    privacy="private_to_tenant",
    permissions=["own_or_authorized_media"],
    billing_policy="METERED_MEDIA",
    evidence={"provider_name": True, "segment_durations": True, "stitch_method": True},
)


# === F. 商品源图 → 图文营销全套 (WP006→007→032→040) ===
WP_PRODUCT_MARKETING = WorkPathDefinition(
    id="WP-PRODUCT-MARKETING",
    revision=1,
    title="商品源图 → 图文营销全套",
    domain="creation",
    goal="源产品图 + 品牌规范 + 卖点 → 多渠道尺寸图 + 短视频 + 平台文案 + 交付包",
    triggers=["用户提供产品图", "用户要求多渠道适配", "用户要求营销全套"],
    preconditions=["产品图可识别", "品牌规范明确"],
    inputs=[
        InputSpec(role="product_image", mime="image/*", min=1, max=1),
        InputSpec(role="brand_spec", mime="text/plain", min=0, max=1),
        InputSpec(role="selling_points", mime="text/plain", min=0, max=1),
    ],
    planner="intent_resolver_v4",
    steps=[
        {"id": "product_verify", "operation": "vision.product_verify", "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "scene_plan", "operation": "product.scene_plan", "requires": ["product_verify"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "channel_resize", "operation": "image.crop_or_outpaint", "requires": ["scene_plan"], "node_kind": "MEDIA_GENERATE", "cost_class": "FREE_LOCAL"},
        {"id": "video_script", "operation": "video.script.generate", "requires": ["scene_plan"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "video_gen", "operation": "video.generate", "requires": ["video_script"], "node_kind": "MEDIA_GENERATE", "cost_class": "METERED_MEDIA", "checkpoint": "budget_approve_media"},
        {"id": "video_tts", "operation": "doubao.tts", "requires": ["video_script"], "node_kind": "MEDIA_GENERATE", "cost_class": "METERED_NONMEDIA"},
        {"id": "copy_platforms", "operation": "content.adapt_platform", "requires": ["video_script"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "compliance_qa", "operation": "content.compliance_check", "requires": ["copy_platforms", "channel_resize"], "node_kind": "MODEL_REASON", "cost_class": "METERED_NONMEDIA"},
        {"id": "package", "operation": "export.package", "requires": ["compliance_qa", "video_gen"], "node_kind": "EXPORT", "cost_class": "FREE_LOCAL"},
    ],
    quality_gates=["all_channels_have_assets", "trademark_clear", "platform_compliance_pass"],
    exported_artifacts=["channel_images", "video", "copy_pack", "package_zip", "manifest"],
    recovery={"retry_failed_only": True},
    privacy="private_to_tenant",
    permissions=["own_or_licensed"],
    billing_policy="MIXED",
    evidence={"channel_versions": True, "compliance_signoff": True},
)


# 单原子能力的完整执行路径：只做真实本地 HTML 提取，不冒充 AI 改写。
# 与 6 类旗舰复杂工作流分开计数。
WP_LOCAL_ARTICLE_EXTRACT = WorkPathDefinition(
    id="WP-LOCAL-ARTICLE-EXTRACT",
    revision=1,
    title="已授权 HTML → 原文与媒体引用提取",
    domain="content",
    goal="使用用户提供的 HTML 提取真实正文、标题、图片与视频引用，"
         "保存任务节点结果，不访问外部 URL，不使用 LLM",
    triggers=["用户已提供授权 HTML 原文"],
    preconditions=["用户具备提供和处理原文的权利"],
    inputs=[
        InputSpec(role="html", mime="text/html", min=1, max=1),
        InputSpec(role="source_url", mime="text/url", min=0, max=1),
    ],
    planner="deterministic_local_executor",
    steps=[
        {
            "id": "html_parse",
            "operation": "article.html_parse",
            "node_kind": "TRANSFORM",
            "cost_class": "FREE_LOCAL",
            "requires": [],
            "produces": ["article_text", "media_refs", "content_sha256"],
            "retries": 0,
        },
    ],
    quality_gates=["input_html_supplied", "content_sha256_present"],
    exported_artifacts=["article_text", "media_refs", "content_sha256"],
    recovery={"manual_reconciliation_only": True},
    privacy="private_to_tenant",
    permissions=["own_or_licensed"],
    billing_policy="FREE_LOCAL",
    evidence={"source_hash": True, "provider_called": False},
)


# 已提供逐句时间戳的字幕转换：不宣称已完成音频 ASR。
WP_LOCAL_SUBTITLE_EXPORT = WorkPathDefinition(
    id="WP-LOCAL-SUBTITLE-EXPORT",
    revision=1,
    title="真实转写片段 → SRT / VTT 字幕",
    domain="content",
    goal="对用户提供的逐句时间戳和真实文本进行校验，输出可直接导出的字幕文本。",
    triggers=["用户已提供带时间戳的字幕片段"],
    preconditions=["转写文本和时间戳均来自用户已获授权的实际素材"],
    inputs=[InputSpec(role="segments", mime="application/json", min=1, max=1)],
    planner="deterministic_local_executor",
    steps=[{
        "id": "subtitle_export",
        "operation": "subtitle.format_supplied",
        "node_kind": "TRANSFORM",
        "cost_class": "FREE_LOCAL",
        "requires": [],
        "produces": ["srt", "vtt", "source_sha256"],
        "retries": 0,
    }],
    quality_gates=["segments_validated", "source_sha256_present"],
    exported_artifacts=["srt", "vtt", "source_sha256"],
    recovery={"manual_reconciliation_only": True},
    privacy="private_to_tenant",
    permissions=["own_or_licensed"],
    billing_policy="FREE_LOCAL",
    evidence={"source_hash": True, "asr_performed": False, "model_called": False},
)


# 总注册表
FLAGSHIP_PATHS: Dict[str, WorkPathDefinition] = {
    WP_BLOGGER_RESEARCH.id: WP_BLOGGER_RESEARCH,
    WP_VIDEO_TRANSCRIBE.id: WP_VIDEO_TRANSCRIBE,
    WP_ARTICLE_REWRITE.id: WP_ARTICLE_REWRITE,
    WP_RENOVATION_FULL.id: WP_RENOVATION_FULL,
    WP_GROWTH_VIDEO.id: WP_GROWTH_VIDEO,
    WP_PRODUCT_MARKETING.id: WP_PRODUCT_MARKETING,
}


# Separate the original six flagship paths from deterministic local paths.
LOCAL_PATHS: Dict[str, WorkPathDefinition] = {
    WP_LOCAL_ARTICLE_EXTRACT.id: WP_LOCAL_ARTICLE_EXTRACT,
    WP_LOCAL_SUBTITLE_EXPORT.id: WP_LOCAL_SUBTITLE_EXPORT,
}
ALL_PATHS: Dict[str, WorkPathDefinition] = {**FLAGSHIP_PATHS, **LOCAL_PATHS}

# 后处理: 将所有 steps dict → StepSpec (便于 type check + serialization)
for _defn in ALL_PATHS.values():
    _defn.steps = _to_steps(_defn.steps)


def list_paths() -> List[Dict]:
    return [p.to_dict() for p in ALL_PATHS.values()]


def get_path(path_id: str) -> WorkPathDefinition:
    if path_id not in ALL_PATHS:
        raise KeyError(f"[WP-001] 未知 workpath {path_id}")
    return ALL_PATHS[path_id]

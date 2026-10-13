# EVIDENCE.md — transcribe adapters (WP-VIDEO-TRANSCRIBE)

## 真实接口调用

| 调用项 | 状态 |
|--------|------|
| ffmpeg subprocess | ✅ 真实调用 (用户机器已安装 ffmpeg) |
| 豆包 ASR API | ❌ mock stub |
| Whisper Local API | ❌ mock stub |
| 快手 ASR API | ❌ mock stub |
| 即梦 ASR API | ❌ mock stub |
| 网络 HTTP 请求 | 0 次 |

## Production Ready

**NO**

## 4 个 ASR Provider Stub 状态

| Provider | Stub | 说明 |
|----------|------|------|
| doubao | ✅ | 默认 provider_hint=auto |
| whisper_local | ✅ | 本地 Whisper.cpp stub |
| kuaishou_asr | ✅ | 快手 ASR stub |
| jimeng_asr | ✅ | 即梦 ASR stub |

## 下一步 (L4 等待 user 拍板)

1. **接豆包 ASR**: 需 user 拍音色/计费模式，方可替换 stub
2. **接 Whisper 本地**: 需用户安装 whisper.cpp 并配置路径
3. **接快手/即梦 ASR**: 需 user 拍板合作方和计费

## Mock 合同

所有 stub 返回值均含 `mock: True`，外部调用方应校验此字段。

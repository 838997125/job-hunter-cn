---
name: job-hunter-cn
description: BOSS直聘自动求职助手。自动搜索职位、深度分析JD、自动投递、AI消息回复。
version: 1.0.0
tags: [求职, BOSS直聘, 自动投递, JD分析]
---

# 求职助手 - BOSS直聘

基于 Playwright 浏览器自动化 + MiniMax 大模型，实现**职位搜索 → JD深度分析 → 智能投递 → 消息监控**全流程。

## 快速配置（5步完成）

### 1️⃣ 复制配置示例

```bash
cp data/user_config.json.example data/user_config.json
```

### 2️⃣ 填入AI API Key

支持 MiniMax（推荐）或其他 OpenAI 兼容格式：

| Provider | Model | 获取地址 |
|---------|-------|---------|
| MiniMax | MiniMax-M2.7 | platform.minimax.chat → 控制台 → API Keys |
| OpenAI | GPT-4o-mini | platform.openai.com |
| DeepSeek | DeepSeek Chat | platform.deepseek.com |

```json
{
  "ai": {
    "provider": "minimax_native",
    "model": "MiniMax-M2.7",
    "api_key": "你的API Key",
    "base_url": "https://api.minimax.chat/v1/text"
  }
}
```

### 3️⃣ 填入高德地图API Key（通勤计算用）

获取地址：lbs.amap.com → 注册 → 控制台 → 创建应用 → 获取 Key

```json
{
  "amap": {
    "key": "你的高德API Key"
  }
}
```

> 通勤时间是重要匹配维度！工具会根据你家到公司实际驾车时间评分。

### 4️⃣ 上传简历PDF

将简历放入：
```
data/resumes/我的简历.pdf
```

配置路径：
```json
{
  "user": {
    "name": "你的姓名",
    "phone": "手机号",
    "email": "邮箱",
    "resume_path": "data/resumes/我的简历.pdf",
    "home_location": "你的家庭住址（用于计算通勤）"
  }
}
```

### 5️⃣ 扫码登录BOSS

首次运行需要扫码（只需一次）：

```bash
python scripts/job_search.py --platform boss --keyword "产品经理" --city "武汉"
```

浏览器弹出后用手机扫码登录BOSS。登录态保存在 `data/browser_profile/`，后续无需再登录。

---

## 使用流程

### 每日求职流程

```bash
# 1. 搜索职位
python scripts/job_search.py --platform boss --keyword "产品经理" --city "武汉" --pages 2

# 2. 深度分析所有JD
python scripts/jd_analyzer.py --batch

# 3. 自动投递（按策略）
python scripts/auto_apply.py --platform boss --auto
```

### 消息监控

HR回复后自动处理（每15分钟检查一次）：

```bash
python scripts/message_monitor.py --once
```

---

## 投递策略

| 规则 | 默认值 | 说明 |
|------|--------|------|
| 最低匹配度 | ≥50% | 低于此分数自动跳过 |
| 薪资下限 | ≥12K | 太低的自动跳过 |
| 每日上限 | 100个 | 防止封号 |
| 红标检测 | 开启 | 传销/电销/可疑公司自动婉拒 |

**HR回复处理：**
- 匹配度 ≥50% → 自动发简历 + 打招呼语
- 匹配度 <50% → 自动发婉拒消息
- 无法评分的 → AI根据简历生成回复

---

## 目录结构

```
job-hunter-cn/
├── SKILL.md
├── README.md
├── scripts/
│   ├── job_search.py        # 职位搜索
│   ├── jd_analyzer.py       # JD深度分析
│   ├── auto_apply.py        # 自动投递
│   └── message_monitor.py   # 消息监控
├── data/
│   ├── user_config.json.example  # 配置示例
│   ├── jobs.json             # 职位列表
│   ├── jd_analysis.json      # 分析结果
│   ├── applications.json     # 投递记录
│   └── resumes/              # 简历PDF
└── templates/
    └── resume_template.html  # 简历模板
```

## 安全说明

以下文件已加入 `.gitignore`，不会上传GitHub：
- `data/user_config.json` — 含API Key
- `data/browser_profile/` — 含BOSS登录态Cookies
- `data/resumes/*.pdf` — 你的简历

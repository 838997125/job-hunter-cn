# 求职助手 - BOSS直聘自动投递

基于 AI + 浏览器自动化，实现**职位搜索 → JD分析 → 自动投递 → 消息监控**的全流程自动化求职工具。

---

## 功能

| 模块 | 说明 |
|------|------|
| 🔍 职位搜索 | 抓取BOSS直聘职位列表，过滤重复 |
| 📊 JD深度分析 | AI读取完整JD内容，评分 + 红标检测 + 通勤计算 |
| 📄 简历投递 | 自动发简历附件 + 个性化打招呼语 |
| 💬 消息监控 | 每15分钟检查HR回复，自动回复（发简历/婉拒） |
| 🎯 智能策略 | 匹配度≥50%才投递，<50%自动婉拒 |

---

## 快速上手

### 第一步：配置文件

复制并修改配置文件：

```bash
cp data/user_config.json.example data/user_config.json
```

编辑 `data/user_config.json`，填入你的真实信息：

```json
{
  "user": {
    "name": "你的姓名",
    "phone": "手机号",
    "email": "邮箱",
    "resume_path": "data/resumes/我的简历.pdf",
    "target_positions": ["产品经理", "B端产品经理"],
    "target_cities": ["武汉"],
    "home_location": "武汉市东西湖区xx小区",
    "experience_years": 10,
    "key_skills": ["产品规划", "数据分析", "AI应用"]
  }
}
```

### 第二步：配置AI API Key

支持 **MiniMax** 或其他兼容 OpenAI 格式的 API：

```json
{
  "ai": {
    "provider": "minimax_native",
    "model": "MiniMax-M2.7",
    "api_key": "填入你的MiniMax API Key",
    "base_url": "https://api.minimax.chat/v1/text"
  }
}
```

> 💡 **MiniMax API Key 获取**：[platform.minimax.chat](https://platform.minimax.chat) → 注册 → 控制台 → API Keys

### 第三步：配置高德地图API（用于通勤计算）

```json
{
  "amap": {
    "key": "填入你的高德地图API Key"
  }
}
```

> 💡 **高德地图API Key获取**：[lbs.amap.com](https://lbs.amap.com) → 注册开发者账号 → 控制台 → 创建应用 → 获取 Key（Web服务API类型）

### 第四步：上传简历

将你的简历PDF放入：

```
data/resumes/我的简历.pdf
```

并在配置中指定路径：
```json
"resume_path": "data/resumes/我的简历.pdf"
```

### 第五步：扫码登录BOSS直聘

首次运行需要扫码登录（只需一次）：

```bash
# 1. 先测试登录
python scripts/job_search.py --platform boss --keyword "产品经理" --city "武汉"

# 浏览器会弹出BOSS直聘登录页面，用手机扫码登录

# 2. 登录成功后，登录态会自动保存到 browser_profile/ 目录
# 后续运行无需再登录
```

---

## 使用流程

### 1. 搜索职位

```bash
python scripts/job_search.py --platform boss --keyword "产品经理" --city "武汉" --pages 2
```

结果保存到 `data/jobs.json`

### 2. JD深度分析

```bash
python scripts/jd_analyzer.py --batch
```

会自动：
- 抓取每个职位的完整JD内容
- 调用AI分析匹配度（技能/行业/经验多维度）
- 通过高德API计算实际通勤时间
- 检测红标关键词（传销/电销/可疑公司）
- 生成个性化打招呼语

### 3. 批量投递

```bash
# 交互式投递（每次确认）
python scripts/auto_apply.py --platform boss --interactive

# 自动投递（按策略自动执行）
python scripts/auto_apply.py --platform boss --auto
```

**投递策略（可自定义）：**

| 规则 | 默认值 | 说明 |
|------|--------|------|
| 最低匹配度 | 50% | <50%的职位自动跳过 |
| 高优匹配度 | 70% | ≥70%用定制打招呼语 |
| 每日上限 | 100个 | 安全阈值，避免封号 |
| 薪资下限 | 12K | 低于此薪资自动跳过 |

### 4. 消息监控（定时自动）

开启后每15分钟自动检查BOSS聊天，有HR回复时自动处理：

```bash
# 手动触发一次
python scripts/message_monitor.py --once

# 持续监控（配合系统定时任务）
python scripts/message_monitor.py --once
```

**消息处理逻辑：**

```
HR主动发来消息
  → 关联到jobs.json中的职位
  → 匹配度 ≥ 50% → 自动发送简历 + 打招呼语
  → 匹配度 < 50% → 自动发送婉拒消息
  → 无法评分的 → AI根据简历内容生成回复
```

---

## 文件说明

```
data/
├── user_config.json     ← ⚠️ 你的配置（含API Key），不提交Git
├── jobs.json           ← 搜索到的职位列表
├── jd_analysis.json    ← JD分析结果
├── applications.json   ← 投递记录
├── browser_profile/    ← ⚠️ BOSS登录态，不提交Git
└── resumes/           ← 你的简历PDF，不提交Git
```

`.gitignore` 已配置忽略以上敏感文件。

---

## 目录结构

```
job-hunter-cn/
├── SKILL.md                      # OpenClaw Skill说明
├── README.md                     # 本文件
├── scripts/
│   ├── job_search.py             # 职位搜索
│   ├── jd_analyzer.py            # JD深度分析（含高德通勤）
│   ├── auto_apply.py            # 自动投递
│   ├── message_monitor.py       # 消息监控
│   ├── resume_generator.py      # 简历生成
│   └── utils/
│       ├── browser.py           # Playwright浏览器封装
│       ├── ai_helper.py         # AI调用封装
│       └── config.py            # 配置加载
├── templates/
│   └── resume_template.html     # 简历HTML模板
└── data/
    └── user_config.json.example  # 配置示例
```

---

## 注意事项

1. **投递频率**：BOSS直聘有反自动化限制，建议间隔5秒以上
2. **账号安全**：建议用小号操作，避免主号被封
3. **简历版本**：不同岗位可准备不同简历版本（默认投递 `data/resumes/` 中的固定简历）
4. **通勤权重**：通勤评分已根据实际驾车时间计算，远距离职位会自动降分
5. **红标检测**：命中传销/电销/可疑描述的职位会自动跳过并婉拒

---

## 未来功能规划

| 功能 | 状态 | 说明 |
|------|------|------|
| 多平台支持 | 🔜 计划中 | 扩展到猎聘、智联招聘、前程无忧 |
| 简历多版本 | 🔜 计划中 | 按JD定制不同简历版本自动投递 |
| 定时任务集成 | 🔜 计划中 | 支持Windows任务计划程序/Cron |
| 投递效果追踪 | 🔜 计划中 | 记录投递后HR是否查看、是否回复 |
| 薪资预测 | 💡 想法中 | 根据公司+职位+地区预测薪资范围 |
| 竞品分析 | 💡 想法中 | 对比同公司同岗位竞争者画像 |
| 面试题库 | 💡 想法中 | 根据投递记录生成面试预测题 |
| 简历效果热图 | 💡 想法中 | AI分析简历各部分被HR关注的热度 |
| 自动跟进提醒 | 💡 想法中 | 投递后N天未回复自动发跟进消息 |
| 多账号管理 | 💡 想法中 | 支持同时管理多个求职账号 |
| 微信通知 | 💡 想法中 | 微信消息推送投递/回复状态 |
| BOSS黑名单 | 💡 想法中 | 标记信誉差的HR和公司 |

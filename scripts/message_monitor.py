#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOSS直聘消息监控 + 智能自动回复
规则：
1. 跳过我们主动发的消息（避免重复）
2. HR主动发来的消息 → 关联jobs.json职位 → 评分≥50%发简历，<50%婉拒
3. 未关联职位的消息 → 抓JD分析 → 决定发/婉拒
4. 其他类型消息 → AI根据简历内容主动回复
"""

import argparse, json, asyncio, re, sys, time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Optional

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from utils.browser import BrowserHelper

DATA_DIR = Path(__file__).parent.parent / "data"
SENT_FILE = DATA_DIR / "monitor_sent.json"
JOBS_FILE = DATA_DIR / "jobs.json"
ANALYSIS_FILE = DATA_DIR / "jd_analysis.json"
RESUME_DEFAULT = "data/resumes/张一钦_简历_202603.pdf"

MIN_MATCH_SCORE = 50

GENERIC_GREETING = (
    "您好，我是张一钦，10年产品经理（6年技术+4年产品），"
    "专注AI与云产品落地，可立即到岗。附件是我的简历，期待进一步沟通！"
)

AI_REFUSE = (
    "您好，感谢您的回复！仔细看了JD后，感觉与我的背景和职业规划略有差异，"
    "就不打扰您了，祝早日找到合适的人才！"
)


def load_user_profile(config) -> Dict:
    return {
        "name": config.user.name,
        "experience_years": config.user.experience_years,
        "work_summary": config.user.work_summary,
        "key_skills": ", ".join(config.user.key_skills) if config.user.key_skills else "",
    }


def ai_reply(message: str, user_profile: Dict, action: str) -> str:
    """AI生成回复（婉拒 or 其他）"""
    if action == "refuse":
        return AI_REFUSE
    
    prompt = f"""你是一个求职者，收到HR的消息后进行专业、友好的回复。

候选人信息：
- 姓名：{user_profile['name']}
- 工作年限：{user_profile['experience_years']}年
- 背景：{user_profile['work_summary']}
- 核心技能：{user_profile['key_skills']}

HR消息：{message}

请生成一个简短、专业的回复（50字以内）：
"""
    return f"您好，感谢您的消息！我会尽快查看，如有兴趣会及时回复您。期待进一步交流！"


def load_jobs() -> List[Dict]:
    if JOBS_FILE.exists():
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_analysis() -> Dict:
    if ANALYSIS_FILE.exists():
        with open(ANALYSIS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_sent() -> Set[str]:
    if SENT_FILE.exists():
        with open(SENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("processed", []))
    return set()


def save_sent(processed: Set[str]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SENT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "processed": list(processed),
            "last_run": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)


def get_resume_path(config) -> str:
    if config.user.resume_path:
        return str(Path(__file__).parent.parent / config.user.resume_path)
    return str(Path(__file__).parent.parent / RESUME_DEFAULT)


async def get_chat_list(browser) -> List[Dict]:
    """获取聊天列表"""
    try:
        await browser.page.wait_for_selector(".chat-user", timeout=10000)
    except:
        pass
    await asyncio.sleep(2)
    try:
        result = await browser.page.evaluate("""
            function() {
                var items = document.querySelectorAll('.chat-user');
                return Array.from(items).map(function(el) {
                    return {
                        id: el.getAttribute('data-id') || '',
                        name: el.querySelector('.name-text') ? el.querySelector('.name-text').textContent.trim() : '',
                        company: el.querySelector('.company') ? el.querySelector('.company').textContent.trim() : '',
                        time: el.querySelector('.time') ? el.querySelector('.time').textContent.trim() : '',
                        msg: el.querySelector('.last-msg-text') ? el.querySelector('.last-msg-text').textContent.trim() : '',
                        unread: el.querySelector('.unread') !== null
                    };
                });
            }
        """)
        return result if isinstance(result, list) else []
    except Exception as e:
        print(f"get_chat_list error: {e}")
        return []


async def get_conversation_messages(browser, conv_id: str) -> List[Dict]:
    """获取某个会话的聊天记录，判断谁先发的消息"""
    # 点击进入会话
    items = await browser.page.query_selector_all(".chat-user")
    target = None
    for item in items:
        did = await item.get_attribute("data-id")
        if did == conv_id:
            target = item
            break

    if target:
        await target.click()
        await asyncio.sleep(2)

    # 等待聊天内容加载
    await asyncio.sleep(1)

    # 获取聊天记录
    msgs = await browser.page.evaluate("""() => {
        const msgs = document.querySelectorAll('.msg-item, .chat-msg-item, [class*=msg-item]');
        return Array.from(msgs).slice(-20).map(el => {
            const isMine = el.querySelector('[class*=mine], [class*=self]') !== null;
            const textEl = el.querySelector('.text, .msg-text, [class*=text]');
            const text = textEl?.textContent?.trim() || '';
            const timeEl = el.querySelector('.time, [class*=time]');
            const time = timeEl?.textContent?.trim() || '';
            return { isMine, text, time };
        }).filter(m => m.text);
    }""")

    return msgs if isinstance(msgs, list) else []


async def quick_analyze_jd(job_id: str, browser) -> Optional[Dict]:
    """快速抓JD做简单评分"""
    try:
        await browser.goto(f"https://www.zhipin.com/job_detail/{job_id}.html",
                         wait_until="domcontentloaded")
        await asyncio.sleep(2)

        jd_el = await browser.page.query_selector(".job-sec-text")
        jd_text = await jd_el.inner_text() if jd_el else ""
        if not jd_text:
            return None

        # 简单红标检测
        red_flags = []
        suspicious = ["传销", "拉人头", "日薪", "周薪", "无责任底薪", "地推", "营销策划"]
        for flag in suspicious:
            if flag in jd_text:
                red_flags.append(flag)

        # 简单评分（关键词命中）
        score = 50
        good_keywords = ["产品经理", "B端", "云", "AI", "互联网", "软件", "数据", "规划", "需求"]
        bad_keywords = ["销售", "客服", "推广", "中介", "保险"]
        for kw in good_keywords:
            if kw in jd_text:
                score += 5
        for kw in bad_keywords:
            if kw in jd_text:
                score -= 10

        score = max(0, min(100, score))
        return {"score": score, "red_flags": red_flags, "jd_text": jd_text[:500]}
    except:
        return None


def match_conv_to_job(conv: Dict, jobs: List[Dict], analysis: Dict) -> Optional[tuple]:
    """将会话与jobs.json职位匹配"""
    company = conv.get("company", "")
    name = conv.get("name", "")
    if not company:
        return None

    for job in jobs:
        jc = job.get("company", "")
        if not jc:
            continue
        if any(kw in jc or jc in kw for kw in [company, name]):
            job_id = job.get("id", "")
            if job_id in analysis:
                score = int(analysis[job_id].get("match_result", {}).get("match_score", 0))
                return (job, score)
    return None


async def send_resume_and_greeting(browser, resume_path: str, greeting: str) -> bool:
    """发送简历+打招呼语"""
    try:
        file_input = await browser.page.query_selector(".upload-resume__old input[type=file]")
        if file_input:
            await file_input.set_input_files(resume_path)
            await asyncio.sleep(2)

        textarea = await browser.page.query_selector("textarea")
        if textarea:
            await textarea.fill(greeting)
            await asyncio.sleep(0.5)

        send_btn = await browser.page.query_selector("[class*=send]")
        if send_btn:
            await send_btn.click(force=True)
            await asyncio.sleep(1)
            return True
        return False
    except Exception as e:
        print(f"  发送异常: {e}")
        return False


async def send_text_reply(browser, text: str) -> bool:
    """发送纯文本消息"""
    try:
        textarea = await browser.page.query_selector("textarea")
        if textarea:
            await textarea.fill(text)
            await asyncio.sleep(0.5)

        send_btn = await browser.page.query_selector("[class*=send]")
        if send_btn:
            await send_btn.click(force=True)
            await asyncio.sleep(1)
            return True
        return False
    except Exception as e:
        print(f"  发送异常: {e}")
        return False


async def run_monitor():
    config = load_config()
    user_profile = load_user_profile(config)
    resume_path = get_resume_path(config)
    processed = load_sent()
    jobs = load_jobs()
    analysis = load_analysis()

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === BOSS消息监控 ===")
    print(f"简历: {Path(resume_path).name} | 最低匹配: {MIN_MATCH_SCORE}%")

    browser = BrowserHelper(headless=False)
    await browser.start()

    try:
        await browser.goto("https://www.zhipin.com/web/geek/chat")
        await asyncio.sleep(5)
        
        # 点击"仅沟通"标签（只显示HR主动发起沟通的）
        try:
            await browser.page.wait_for_selector(".filter-tab, .tab-item", timeout=5000)
            tabs = await browser.page.query_selector_all(".filter-tab .tab-item, .tab-item")
            for t in tabs:
                txt = await t.inner_text()
                if "仅沟通" in txt:
                    await t.click()
                    print("  点击了「仅沟通」标签")
                    await asyncio.sleep(2)
                    break
        except:
            pass
        # 等待聊天列表加载
        try:
            await browser.page.wait_for_selector(".chat-user", timeout=10000)
        except:
            pass
        await asyncio.sleep(2)

        convs = await get_chat_list(browser)
        print(f"发现 {len(convs)} 个会话")

        new_convs = [c for c in convs if c["id"] and c["id"] not in processed]
        print(f"待处理: {len(new_convs)} 个")

        for conv in new_convs:
            print(f"\n处理: {conv['name']} | {conv['company']} | {conv['time']}")
            print(f"  最后消息: {conv['msg'][:60]}")

            # 获取聊天记录判断谁先发的
            msgs = await get_conversation_messages(browser, conv["id"])
            if not msgs:
                print("  无法获取聊天记录，跳过")
                processed.add(conv["id"])
                continue

            last_msgs = msgs[-3:]  # 最近3条
            our_last = None
            for m in reversed(last_msgs):
                if m.get("isMine"):
                    our_last = m
                    break

            if our_last:
                print("  跳过：我们主动发的消息")
                processed.add(conv["id"])
                continue

            # HR主动发的消息
            print("  → HR主动发来的消息，需要处理")

            # 关联jobs.json
            matched = match_conv_to_job(conv, jobs, analysis)

            if matched:
                job, score = matched
                print(f"  关联职位: {job.get('title')} (匹配度{score}%)")
            else:
                score = None
                print("  未关联到jobs.json，快速分析JD...")

                # 从会话消息中找job_id（BOSS聊天里可能有职位链接）
                last_msg = conv.get("msg", "")
                job_id_match = re.search(r'/job_detail/([a-zA-Z0-9]+)', last_msg)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    result = await quick_analyze_jd(job_id, browser)
                    if result:
                        score = result["score"]
                        print(f"  快速评分: {score}% | 红标: {result['red_flags']}")

            # 决定行动
            if score is not None and score < MIN_MATCH_SCORE:
                print(f"  → 婉拒（{score}% < {MIN_MATCH_SCORE}%）")
                ok = await send_text_reply(browser, AI_REFUSE)
                if ok:
                    processed.add(conv["id"])
            elif score is not None:
                print(f"  → 发送简历+打招呼语（{score}% >= {MIN_MATCH_SCORE}%）")
                ok = await send_resume_and_greeting(browser, resume_path, GENERIC_GREETING)
                if ok:
                    processed.add(conv["id"])
            else:
                # 无法评分的，发一个通用回复
                print("  → 无法评分，发送通用回复")
                reply = ai_reply(conv.get("msg", ""), user_profile, "other")
                ok = await send_text_reply(browser, reply)
                if ok:
                    processed.add(conv["id"])

        save_sent(processed)
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 完成，待处理 {len(new_convs)} 个")

    finally:
        await browser.close()


def main():
    parser = argparse.ArgumentParser(description="BOSS消息监控")
    parser.add_argument("--once", "-o", action="store_true", help="运行一次后退出")
    parser.add_argument("--interval", "-i", type=int, default=30, help="检查间隔（分钟）")
    args = parser.parse_args()

    if args.once:
        asyncio.run(run_monitor())
    else:
        while True:
            asyncio.run(run_monitor())
            print(f"等待 {args.interval} 分钟后再次检查...")
            time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()

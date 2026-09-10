#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
求职助手 - 自动投递模块
策略：匹配度过滤 + 薪资过滤 + 查重 + 每日限额 + 智能打招呼语
"""

import argparse
import json
import asyncio
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from utils.browser import BrowserHelper, BossZhipinClient, JobInfo


DATA_DIR = Path(__file__).parent.parent / "data"
SKILL_ROOT = Path(__file__).parent.parent
JOBS_FILE = DATA_DIR / "jobs.json"
ANALYSIS_FILE = DATA_DIR / "jd_analysis.json"
APPLICATIONS_FILE = DATA_DIR / "applications.json"

# ===== 投递策略配置 =====
MIN_MATCH_SCORE = 50       # 最低匹配度（低于此跳过）
HIGH_MATCH_SCORE = 70      # 高匹配度（优先投递+定制语）
MIN_SALARY_K = 12          # 薪资下限（K）
MAX_DAILY = 100            # 每日最高投递数（安全阈值）
GENERAL_GREETING = "您好，我是张一钦，10年产品经验，6年技术+4年产品，专注AI与云产品落地，可立即到岗。期待与您沟通，谢谢！"  # 通用打招呼语


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


def load_applications() -> List[Dict]:
    if APPLICATIONS_FILE.exists():
        with open(APPLICATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_application(application: Dict):
    applications = load_applications()
    existing_ids = {a["job_id"] for a in applications}
    if application["job_id"] not in existing_ids:
        applications.append(application)
    with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(applications, f, ensure_ascii=False, indent=2)


def parse_salary(salary_str: str) -> Optional[int]:
    """从薪资字符串提取最低薪资（单位K），返回如 18 或 None"""
    import re
    # 如 "18-30K" 或 "15K" 或 "面议"
    cleaned = salary_str.replace("\u200b", "").replace("K", "k")
    nums = re.findall(r'(\d+)', cleaned)
    if not nums:
        return None
    return int(nums[0])


def get_match_score(job_id: str, analysis: Dict) -> int:
    """获取职位匹配度分数"""
    if job_id in analysis:
        score = analysis[job_id].get("match_result", {}).get("match_score", 0)
        return int(score)
    return 0


def get_custom_greeting(job_id: str, analysis: Dict) -> str:
    """获取定制打招呼语"""
    if job_id in analysis:
        greeting = analysis[job_id].get("greeting", "")
        if greeting and len(greeting) > 10:
            return greeting
    return GENERAL_GREETING


def filter_and_rank_jobs(jobs: List[Dict], analysis: Dict, apps: List[Dict]) -> List[Dict]:
    """过滤+排序职位
    
    规则：
    1. 匹配度 < MIN_MATCH_SCORE → 跳过
    2. 薪资 < MIN_SALARY_K → 跳过
    3. 同公司+同职位已投 → 跳过
    4. 按匹配度从高到低排序
    """
    applied_keys = {(a["company"], a["title"]) for a in apps}
    today = datetime.now().date()
    today_apps = [a for a in apps if datetime.fromisoformat(a["apply_time"]).date() == today]
    
    # 统计今日已投数
    daily_count = len(today_apps)
    remaining = MAX_DAILY - daily_count
    
    print(f"\n📊 投递统计：今日已投 {daily_count} 个，剩余配额 {remaining} 个")
    
    filtered = []
    skipped = []
    
    for job in jobs:
        # 跳过已投递（job_id查重）
        if any(a["job_id"] == job["id"] for a in apps):
            skipped.append(f"  ⏭ 已投过: {job['company']} - {job['title']}")
            continue
        
        # 跳过同公司同职位
        key = (job.get("company", ""), job.get("title", ""))
        if key in applied_keys:
            skipped.append(f"  ⏭ 同公司已投: {job['company']} - {job['title']}")
            continue
        
        # 匹配度过滤
        score = get_match_score(job["id"], analysis)
        if score > 0 and score < MIN_MATCH_SCORE:
            skipped.append(f"  ⏭ 匹配度{score}%: {job['company']} - {job['title']}")
            continue
        
        # 薪资过滤
        salary_str = job.get("salary", "")
        min_salary = parse_salary(salary_str)
        if min_salary is not None and min_salary < MIN_SALARY_K:
            skipped.append(f"  ⏭ 薪资{min_salary}K: {job['company']} - {job['title']}")
            continue
        
        # 标记优先级
        priority = 2 if score >= HIGH_MATCH_SCORE else 1
        filtered.append({**job, "_match_score": score, "_priority": priority})
    
    # 按优先级和匹配度排序（高优先级在前，同优先级按分数降序）
    filtered.sort(key=lambda x: (x["_priority"], x["_match_score"]), reverse=True)
    
    # 打印跳过原因
    if skipped:
        for s in skipped[:10]:  # 最多显示10条
            print(s)
        if len(skipped) > 10:
            print(f"  ... 还有 {len(skipped)-10} 个职位被跳过")
    
    # 限制每日投递数
    if remaining <= 0:
        print("\n⚠️ 今日配额已用完，明日再投！")
        return []
    
    if len(filtered) > remaining:
        print(f"\n⚠️ 职位数量({len(filtered)})超过剩余配额({remaining})，取前{remaining}个")
        filtered = filtered[:remaining]
    
    return filtered


async def auto_apply_boss(jobs: List[Dict], greetings: Dict,
                          resume_path: str = "",
                          delay: int = 5, headless: bool = False,
                          confirm: bool = True):
    """自动投递BOSS直聘"""
    browser = BrowserHelper(headless=headless)
    await browser.start()
    
    client = BossZhipinClient(browser)
    
    # 检查登录态
    await browser.goto("https://www.zhipin.com/web/geek/job?query=产品经理&city=101200100")
    await asyncio.sleep(2)
    if "web/geek" not in browser.page.url:
        print("请在浏览器中登录BOSS直聘...")
        try:
            await browser.page.wait_for_url("**/web/geek/**", timeout=30000)
        except:
            print("❌ 登录超时")
            await browser.close()
            return []
    
    print("✅ 已确认登录状态")
    
    applied = []
    
    for i, job in enumerate(jobs):
        score = job.get("_match_score", 0)
        priority_label = "🔥优先" if job.get("_priority", 0) >= 2 else "普通"
        
        print(f"\n[{i+1}/{len(jobs)}] {priority_label} 匹配度{score}%: {job['title']} - {job['company']}")
        
        # 获取打招呼语（高分用定制语，低分用通用语）
        if score >= HIGH_MATCH_SCORE:
            greeting = greetings.get(job["id"], {}).get("greeting", "") or GENERAL_GREETING
            print(f"  → 使用定制打招呼语")
        else:
            greeting = GENERAL_GREETING
            print(f"  → 使用通用打招呼语")
        
        if confirm:
            ans = input("  投递？[y/n/q]: ").lower()
            if ans == 'q':
                print("停止投递")
                break
            elif ans != 'y':
                print("  跳过")
                continue
        
        try:
            success = await client.apply_job(job["id"], greeting, resume_path)
            
            if success:
                record = {
                    "job_id": job["id"],
                    "title": job["title"],
                    "company": job["company"],
                    "salary": job.get("salary", ""),
                    "match_score": score,
                    "platform": "boss",
                    "apply_time": datetime.now().isoformat(),
                    "status": "applied",
                    "greeting": greeting[:50] + "..." if len(greeting) > 50 else greeting
                }
                save_application(record)
                applied.append(record)
                applied_keys = {(job.get("company", ""), job.get("title", ""))}
            
            await asyncio.sleep(delay)
            
        except Exception as e:
            print(f"  ❌ 投递失败: {e}")
    
    await browser.close()
    return applied


def main():
    parser = argparse.ArgumentParser(description="自动投递 - BOSS直聘")
    parser.add_argument("--platform", "-p", default="boss", help="平台")
    parser.add_argument("--jobs", "-j", help="职位文件路径")
    parser.add_argument("--job-id", help="单个职位ID")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互确认")
    parser.add_argument("--auto", "-a", action="store_true", help="自动模式（不确认）")
    parser.add_argument("--delay", "-d", type=int, default=5, help="投递间隔(秒)")
    parser.add_argument("--limit", "-l", type=int, default=20, help="最大投递数（参考）")
    
    args = parser.parse_args()
    
    config = load_config()
    
    print("=" * 50)
    print("自动投递 - BOSS直聘")
    print("=" * 50)
    print(f"策略：匹配度≥{MIN_MATCH_SCORE}% | 薪资≥{MIN_SALARY_K}K | 每日上限{MAX_DAILY}个")
    
    # 加载数据
    if args.jobs:
        with open(args.jobs, "r", encoding="utf-8") as f:
            jobs = json.load(f)
    else:
        jobs = load_jobs()
    
    analysis = load_analysis()
    apps = load_applications()
    greetings = {k: {"greeting": v.get("greeting", "")} for k, v in analysis.items()}
    
    # 单个职位模式
    if args.job_id:
        jobs = [j for j in jobs if j["id"] == args.job_id]
    
    print(f"\n原始职位数: {len(jobs)} 个")
    
    # 过滤+排序
    ranked_jobs = filter_and_rank_jobs(jobs, analysis, apps)
    
    if not ranked_jobs:
        print("\n没有可投递的职位")
        return
    
    print(f"\n✅ 可投递: {len(ranked_jobs)} 个")
    
    # 打印待投列表（不重复）
    for i, job in enumerate(ranked_jobs[:10]):
        score = job.get("_match_score", 0)
        print(f"  [{i+1}] {score}% {job['title']} - {job['company']}")
    if len(ranked_jobs) > 10:
        print(f"  ... 还有 {len(ranked_jobs)-10} 个")
    
    # 简历
    resume_path = str(SKILL_ROOT / config.user.resume_path) if config.user.resume_path else ""
    if resume_path and Path(resume_path).exists():
        print(f"\n📎 简历: {Path(resume_path).name}")
    else:
        resume_path = ""
        print(f"\n⚠️ 未找到简历，将只发打招呼语")
    
    # 执行
    applied = asyncio.run(auto_apply_boss(
        ranked_jobs,
        greetings,
        resume_path=resume_path,
        delay=args.delay,
        headless=args.headless,
        confirm=not args.auto
    ))
    
    print("\n" + "=" * 50)
    print(f"投递完成，共投递 {len(applied)} 个职位")
    print("=" * 50)
    
    if applied:
        print("\n本次投递记录：")
        for r in applied:
            print(f"  ✅ {r['company']} - {r['title']} (匹配度{r.get('match_score',0)}%)")


if __name__ == "__main__":
    main()

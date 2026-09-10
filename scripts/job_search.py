#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
求职助手 - 职位搜索模块
"""

import argparse
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 添加路径
import sys
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from utils.browser import BrowserHelper, BossZhipinClient, LiepinClient, JobInfo


DATA_DIR = Path(__file__).parent.parent / "data"
JOBS_FILE = DATA_DIR / "jobs.json"


def save_jobs(jobs: List[Dict], append: bool = True):
    """保存职位数据"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if append and JOBS_FILE.exists():
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        # 去重
        existing_ids = {j["id"] for j in existing}
        for job in jobs:
            if job["id"] not in existing_ids:
                existing.append(job)
        jobs = existing
    
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已保存 {len(jobs)} 个职位到 {JOBS_FILE}")


async def search_boss(keyword: str, city: str, pages: int = 3, headless: bool = False):
    """搜索BOSS直聘职位"""
    browser = BrowserHelper(headless=headless)
    await browser.start()
    
    client = BossZhipinClient(browser)
    
    # 需要先登录
    print("请在浏览器中登录BOSS直聘...")
    logged_in = await client.login_qrcode()
    
    if not logged_in:
        await browser.close()
        return []
    
    all_jobs = []
    
    for page in range(1, pages + 1):
        print(f"\n搜索第 {page} 页...")
        jobs = await client.search_jobs(keyword, city, page)
        
        for job in jobs:
            all_jobs.append({
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "salary": job.salary,
                "location": job.location,
                "jd_url": job.jd_url,
                "platform": "boss",
                "search_keyword": keyword,
                "search_city": city,
                "search_time": datetime.now().isoformat()
            })
        
        print(f"找到 {len(jobs)} 个职位")
        await asyncio.sleep(2)  # 避免请求过快
    
    await browser.close()
    return all_jobs


def main():
    parser = argparse.ArgumentParser(description="职位搜索")
    parser.add_argument("--platform", "-p", default="boss", 
                        choices=["boss", "liepin", "all"], help="平台选择")
    parser.add_argument("--keyword", "-k", required=True, help="搜索关键词")
    parser.add_argument("--city", "-c", default="武汉", help="城市")
    parser.add_argument("--pages", "-n", type=int, default=3, help="搜索页数")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--output", "-o", help="输出文件")
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    print("=" * 50)
    print(f"职位搜索 - {args.platform}")
    print(f"关键词: {args.keyword}")
    print(f"城市: {args.city}")
    print("=" * 50)
    
    all_jobs = []
    
    if args.platform in ["boss", "all"]:
        jobs = asyncio.run(search_boss(
            args.keyword, args.city, args.pages, args.headless
        ))
        all_jobs.extend(jobs)
    
    if args.platform in ["liepin", "all"]:
        # TODO: 猎聘搜索
        print("猎聘搜索功能开发中...")
    
    # 保存结果
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 结果已保存到: {output_path}")
    else:
        save_jobs(all_jobs)
    
    # 打印统计
    print("\n" + "=" * 50)
    print(f"共找到 {len(all_jobs)} 个职位")
    print("=" * 50)


if __name__ == "__main__":
    main()
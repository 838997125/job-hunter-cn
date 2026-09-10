#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
求职助手 - 投递追踪模块
"""

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from collections import Counter


DATA_DIR = Path(__file__).parent.parent / "data"
APPLICATIONS_FILE = DATA_DIR / "applications.json"


def load_applications() -> List[Dict]:
    """加载投递记录"""
    if APPLICATIONS_FILE.exists():
        with open(APPLICATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_applications(applications: List[Dict]):
    """保存投递记录"""
    with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(applications, f, ensure_ascii=False, indent=2)


def list_applications(limit: int = 20, status: str = None):
    """列出投递记录"""
    applications = load_applications()
    
    if status:
        applications = [a for a in applications if a.get("status") == status]
    
    # 按时间倒序
    applications.sort(key=lambda x: x.get("apply_time", ""), reverse=True)
    
    print("=" * 80)
    print(f"投递记录 (共 {len(applications)} 条)")
    print("=" * 80)
    
    for i, app in enumerate(applications[:limit]):
        time_str = app.get("apply_time", "")[:10]
        print(f"[{i+1}] {time_str} | {app['title']} | {app['company']} | {app.get('salary', '')} | {app.get('status', 'applied')}")
    
    if len(applications) > limit:
        print(f"... 还有 {len(applications) - limit} 条记录")


def show_stats():
    """显示统计信息"""
    applications = load_applications()
    
    if not applications:
        print("暂无投递记录")
        return
    
    print("=" * 60)
    print("投递统计")
    print("=" * 60)
    
    # 总数
    print(f"总投递数: {len(applications)}")
    
    # 按平台
    platforms = Counter(a.get("platform", "unknown") for a in applications)
    print(f"\n按平台:")
    for p, c in platforms.items():
        print(f"  {p}: {c}")
    
    # 按状态
    statuses = Counter(a.get("status", "applied") for a in applications)
    print(f"\n按状态:")
    for s, c in statuses.items():
        print(f"  {s}: {c}")
    
    # 按日期
    dates = Counter(a.get("apply_time", "")[:10] for a in applications)
    print(f"\n按日期（近7天）:")
    for d, c in sorted(dates.items(), reverse=True)[:7]:
        print(f"  {d}: {c}")
    
    # 今日投递
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = dates.get(today, 0)
    print(f"\n今日投递: {today_count}")


def update_status(job_id: str, status: str):
    """更新投递状态"""
    applications = load_applications()
    
    for app in applications:
        if app["job_id"] == job_id:
            app["status"] = status
            app["update_time"] = datetime.now().isoformat()
            break
    
    save_applications(applications)
    print(f"✅ 已更新状态: {job_id} -> {status}")


def export_applications(output: str):
    """导出投递记录"""
    applications = load_applications()
    
    # 生成Markdown报告
    md = """# 投递记录

| 日期 | 岗位 | 公司 | 薪资 | 状态 |
|------|------|------|------|------|
"""
    
    for app in sorted(applications, key=lambda x: x.get("apply_time", ""), reverse=True):
        time_str = app.get("apply_time", "")[:10]
        md += f"| {time_str} | {app['title']} | {app['company']} | {app.get('salary', '-')} | {app.get('status', 'applied')} |\n"
    
    with open(output, "w", encoding="utf-8") as f:
        f.write(md)
    
    print(f"✅ 已导出到: {output}")


def main():
    parser = argparse.ArgumentParser(description="投递追踪")
    parser.add_argument("--list", "-l", action="store_true", help="列出投递记录")
    parser.add_argument("--stats", "-s", action="store_true", help="显示统计")
    parser.add_argument("--update", "-u", nargs=2, metavar=("JOB_ID", "STATUS"), help="更新状态")
    parser.add_argument("--export", "-e", metavar="FILE", help="导出报告")
    parser.add_argument("--limit", type=int, default=20, help="显示数量")
    
    args = parser.parse_args()
    
    if args.list:
        list_applications(limit=args.limit)
    elif args.stats:
        show_stats()
    elif args.update:
        update_status(args.update[0], args.update[1])
    elif args.export:
        export_applications(args.export)
    else:
        # 默认显示统计
        show_stats()


if __name__ == "__main__":
    main()
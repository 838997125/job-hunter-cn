#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JD分析与简历优化模块
- 先抓取JD详情页全文
- 再做深度AI分析（技能+职责+行业+通勤+风险检测）
"""

import argparse
import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from utils.browser import BrowserHelper
from utils.ai_helper import AIHelper

DATA_DIR = Path(__file__).parent.parent / "data"
JOBS_FILE = DATA_DIR / "jobs.json"
ANALYSIS_FILE = DATA_DIR / "jd_analysis.json"

# ===== 高德API配置 =====

AMAP_KEY = "576cb057a9d8318ea5cc39dfc4acf21c"
HOME_COORDS = "114.192875,30.647749"  # 东西湖区金珠港湾2期

# 通勤缓存：(location_str) -> minutes
COMMUTE_CACHE: Dict[str, int] = {}

import requests

def geocode_amap(address: str) -> Optional[str]:
    """高德地理编码：地址 → 经纬度"""
    if not address or address in ("未知", "工作地址"):
        return None
    try:
        resp = requests.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params={"address": address, "city": "武汉", "key": AMAP_KEY},
            timeout=8
        )
        data = resp.json()
        if data.get("status") == "1" and int(data.get("count", 0)) > 0:
            return data["geocodes"][0]["location"]
    except:
        pass
    return None

def calc_commute_minutes(location: str) -> Optional[int]:
    """通过高德API计算实际通勤时间（分钟）"""
    if not location:
        return None
    if location in COMMUTE_CACHE:
        return COMMUTE_CACHE[location]
    
    coords = geocode_amap(location)
    if not coords:
        return None
    
    try:
        resp = requests.get(
            "https://restapi.amap.com/v3/direction/driving",
            params={
                "origin": HOME_COORDS,
                "destination": coords,
                "key": AMAP_KEY,
                "strategy": 0
            },
            timeout=8
        )
        data = resp.json()
        if data.get("status") == "1":
            r = data.get("route", {}).get("paths", [{}])[0]
            minutes = int(r.get("duration", 0)) // 60
            COMMUTE_CACHE[location] = minutes
            return minutes
    except:
        pass
    return None

def calc_commute_score(location: str) -> Dict:
    """基于高德API实际通勤时间计算评分
    
    通勤时间权重（从家到工作地）：
    <30min: +5分（理想）
    30-45min: +3分（良好）
    45-60min: 0分（可接受）
    60-90min: -3分（偏远）
    >90min: -5分（太远）
    """
    minutes = calc_commute_minutes(location)
    if minutes is None:
        return {"commute_min": 0, "commute_bonus": 0, "commute_source": "unknown"}
    
    if minutes < 30:
        bonus = 5
    elif minutes <= 45:
        bonus = 3
    elif minutes <= 60:
        bonus = 0
    elif minutes <= 90:
        bonus = -3
    else:
        bonus = -5
    
    return {"commute_min": minutes, "commute_bonus": bonus, "commute_source": "amap"}

# ===== 红标关键词（命中则降可信度或直接标记）=====
RED_FLAGS = [
    "传销", "拉人头", "保健品", "微商", "直销",
    "日薪", "周薪", "无责任底薪",
    "地推", "推广员", "刷单", "返利",
    "客服", "销售", "业务员",  # 结构性红标（非PM岗位）
]

# ===== 可疑公司名关键词 =====
SUSPICIOUS_COMPANY = [
    "营销策划", "企业管理咨询", "信息科技",  # 名头大的小公司
]


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


def save_analysis_record(job_id: str, record: Dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if ANALYSIS_FILE.exists():
        with open(ANALYSIS_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {}
    existing[job_id] = record
    with open(ANALYSIS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def check_red_flags(jd_text: str, company: str, title: str) -> Dict:
    """检测红标和可疑关键词"""
    text = jd_text + company + title
    text_lower = text.lower()
    hits = []
    for flag in RED_FLAGS:
        if flag in text:
            hits.append(flag)
    for flag in SUSPICIOUS_COMPANY:
        if flag in company:
            hits.append(f"可疑公司:{flag}")
    return {
        "has_red_flags": len(hits) > 0,
        "red_flags": hits
    }


def calc_commute_score(location: str) -> Dict:
    """计算通勤评分
    
    以东西湖区金珠港湾为基准：
    - 光谷/软件园/金融港/吴家山：25-35分钟，+5分（加分）
    - 洪山区/江夏区核心区：35-50分钟，+0分
    - 武昌/汉口核心区：50-70分钟，-3分
    - 远城区/黄陂/新洲：>70分钟，-5分
    """
    loc = location.lower()
    if any(kw in loc for kw in ["光谷", "软件园", "金融港", "吴家山", "洪山区", "珞狮", "街道口"]):
        commute_min = 30
        bonus = 5
    elif any(kw in loc for kw in ["江夏", "武昌", "青山"]):
        commute_min = 45
        bonus = 0
    elif any(kw in loc for kw in ["汉口", "江岸", "江汉", "硚口"]):
        commute_min = 55
        bonus = -3
    elif any(kw in loc for kw in ["东西湖", "黄陂", "新洲", "蔡甸", "汉南"]):
        if "东西湖" in loc:
            commute_min = 15
            bonus = 8
        else:
            commute_min = 70
            bonus = -5
    else:
        commute_min = 50
        bonus = 0
    
    return {"commute_min": commute_min, "commute_bonus": bonus}


def parse_location(raw_text: str) -> str:
    """从BOSS返回的多行地址文本中提取实际地址
    
    BOSS的地址格式通常是：
    "工作地址\n武汉市洪山区小米武汉总部大楼3楼\n\n点击查看地图"
    我们只需要第二行（实际街道地址）
    """
    if not raw_text:
        return ""
    lines = raw_text.split("\n")
    # 取第二行（索引1）通常是实际地址
    if len(lines) >= 2:
        addr = lines[1].strip()
        # 去掉末尾的「点击查看地图」
        addr = addr.replace("点击查看地图", "").strip()
        return addr
    # 否则取第一行非空行
    for line in lines:
        line = line.strip().replace("点击查看地图", "")
        if line and line not in ("工作地址", "公司地址"):
            return line
    return raw_text.strip().replace("点击查看地图", "")


async def fetch_jd_text(job_id: str, browser: BrowserHelper) -> tuple:
    """抓取JD详情页全文，返回(jd_text, location)"""
    try:
        url = f"https://www.zhipin.com/job_detail/{job_id}.html"
        await browser.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # 抓JD正文
        jd_el = await browser.page.query_selector(".job-sec-text")
        jd_text = await jd_el.inner_text() if jd_el else ""
        
        # 抓公司地址（用于通勤计算）
        addr_el = await browser.page.query_selector(".job-location-text, .location-name, [class*=address]")
        raw_loc = await addr_el.inner_text() if addr_el else ""
        location = parse_location(raw_loc)
        
        return jd_text, location
    except Exception as e:
        return "", ""


def analyze_jd_deep(jd_text: str, location: str, user_profile: Dict, ai: AIHelper) -> Dict:
    """深度AI分析：技能匹配 + 职责匹配 + 行业匹配 + 通勤"""
    
    # 基础通勤分
    commute_info = calc_commute_score(location)
    
    prompt = f"""你是一个专业的产品经理HR分析师。请严格评审以下JD，判断候选人是否匹配。

## 候选人背景
姓名：{user_profile['name']}
工作年限：{user_profile['experience_years']}年
核心技能：{', '.join(user_profile['key_skills'])}
职业背景：{user_profile['work_summary']}
目标岗位：{', '.join(user_profile['target_positions'])}

## 职位描述（完整原文）
{jd_text[:3000]}

## 通勤信息
候选人家在武汉市东西湖区金珠港湾2期，该职位工作地点：{location}，预估通勤时间：{commute_info['commute_min']}分钟

## 分析要求
请输出JSON格式的深度分析：

{{
    "jd_summary": "JD核心内容摘要，1-2句话",
    "actual_position_type": "实际岗位类型（PM/销售/运营/其他）",
    "required_skills": ["必需技能1", "必需技能2"],
    "preferred_skills": ["加分技能1"],
    "industry": "所属行业",
    "core_responsibilities": ["核心职责1", "核心职责2"],
    "skill_match_score": 75,
    "responsibility_match_score": 80,
    "industry_match_score": 70,
    "experience_match_score": 85,
    "overall_match_score": 78,
    "matched_skills": ["匹配的技能"],
    "missing_skills": ["明显缺失的技能"],
    "red_flags": ["风险提示：如'需销售指标'、'无五险一金'等"],
    "position_concerns": ["岗位真实性顾虑：如描述模糊、薪资与岗位不符等"],
    "suggestions": ["对候选人的建议"],
    "is_recommended": true,
    "not_recommended_reason": "如果is_recommended=false，说明原因"
}}

注意：
1. skill_match_score：技能关键词匹配度（30%权重）
2. responsibility_match_score：职责匹配度（25%权重）  
3. industry_match_score：行业匹配度（20%权重）
4. experience_match_score：经验匹配度（25%权重）
5. 最终总分 = 加权平均 + 通勤加分({commute_info['commute_bonus']}分)
6. 如果岗位本质是销售/客服/推广（非PM），直接标记is_recommended=false
7. 如果JD描述模糊、薪资异常、或有可疑描述，必须在red_flags或position_concerns中说明

直接输出JSON，不要有其他文字："""

    try:
        result = ai.chat([{"role": "user", "content": prompt}], temperature=0.3)
        start = result.find("{")
        end = result.rfind("}") + 1
        if start != -1 and end != 0:
            analysis = json.loads(result[start:end])
        else:
            analysis = {"raw": result, "error": "JSON解析失败"}
    except Exception as e:
        analysis = {"error": str(e)}
    
    # 加上通勤信息
    analysis["commute_info"] = commute_info
    
    # 计算最终分 = 加权平均 + 通勤
    if "overall_match_score" in analysis and "error" not in analysis:
        base = analysis["overall_match_score"]
        commute_bonus = commute_info["commute_bonus"]
        final = max(0, min(100, base + commute_bonus))
        analysis["final_match_score"] = final
    else:
        analysis["final_match_score"] = 50
    
    # 生成打招呼语
    greeting = generate_greeting(analysis, user_profile)
    analysis["greeting"] = greeting
    
    return analysis


def generate_greeting(analysis: Dict, user_profile: Dict) -> str:
    """根据分析结果生成打招呼语"""
    score = analysis.get("final_match_score", 50)
    matched = analysis.get("matched_skills", [])[:3]
    
    matched_str = "、".join(matched) if matched else "产品规划与数据分析"
    
    if score >= 85:
        greeting = f"您好，我是{user_profile['name']}，{user_profile['experience_years']}年产品经验（{user_profile['experience_years']-4}年技术+4年产品），擅长{matched_str}，专注B端产品与AI落地。看过贵司JD后深感契合，期待进一步沟通！"
    elif score >= 70:
        greeting = f"您好，我是{user_profile['name']}，{user_profile['experience_years']}年经验，擅长{matched_str}，有AI与云计算落地经验。贵司岗位让我很感兴趣，希望能有机会聊聊！"
    else:
        greeting = f"您好，我是{user_profile['name']}，{user_profile['experience_years']}年产品经验，擅长产品规划与需求分析。期待能有机会进一步沟通，谢谢！"
    
    return greeting


async def batch_analyze(jobs: List[Dict], ai: AIHelper, user_profile: Dict, 
                        min_score: int = 0, browser: Optional[BrowserHelper] = None) -> List[Dict]:
    """批量分析JD"""
    results = []
    
    for i, job in enumerate(jobs):
        job_id = job["id"]
        print(f"\n[{i+1}/{len(jobs)}] 分析: {job['title']} - {job['company']}")
        
        # 跳过无效job_id
        if job_id == "boss-test-001":
            print(f"  跳过无效职位ID")
            continue
        
        # 先检查红标（快速过滤）
        title = job.get("title", "")
        company = job.get("company", "")
        
        # 抓JD全文
        if browser:
            jd_text, location = await fetch_jd_text(job_id, browser)
            if not jd_text:
                print(f"  ⚠️ JD抓取失败，跳过")
                continue
            print(f"  JD长度: {len(jd_text)}字符 | 地点: {location or '未知'}")
        else:
            jd_text = job.get("jd_text", f"{title} {company}")
            location = job.get("location", "")
        
        # 快速红标检测
        red_check = check_red_flags(jd_text, company, title)
        if red_check["has_red_flags"]:
            print(f"  🚩 红标命中: {', '.join(red_check['red_flags'])}")
        
        # AI深度分析
        print(f"  AI分析中...")
        analysis = analyze_jd_deep(jd_text, location, user_profile, ai)
        
        # 保存结果
        record = {
            "job_id": job_id,
            "title": title,
            "company": company,
            "salary": job.get("salary", ""),
            "location": location,
            "jd_text": jd_text[:500],
            "jd_analysis": {
                "jd_summary": analysis.get("jd_summary", ""),
                "actual_position_type": analysis.get("actual_position_type", ""),
                "required_skills": analysis.get("required_skills", []),
                "industry": analysis.get("industry", ""),
                "core_responsibilities": analysis.get("core_responsibilities", []),
            },
            "match_result": {
                "match_score": analysis.get("final_match_score", 50),
                "skill_match": analysis.get("skill_match_score", 0),
                "responsibility_match": analysis.get("responsibility_match_score", 0),
                "industry_match": analysis.get("industry_match_score", 0),
                "experience_match": analysis.get("experience_match_score", 0),
                "commute_bonus": analysis.get("commute_info", {}).get("commute_bonus", 0),
                "matched_skills": analysis.get("matched_skills", []),
                "missing_skills": analysis.get("missing_skills", []),
            },
            "red_flags": red_check["red_flags"] + analysis.get("red_flags", []),
            "position_concerns": analysis.get("position_concerns", []),
            "is_recommended": analysis.get("is_recommended", True),
            "not_recommended_reason": analysis.get("not_recommended_reason", ""),
            "greeting": analysis.get("greeting", ""),
        }
        
        save_analysis_record(job_id, record)
        
        score = analysis.get("final_match_score", 50)
        recommended = "✅" if analysis.get("is_recommended", True) else "🚩"
        commute = analysis.get("commute_info", {}).get("commute_min", 0)
        print(f"  {recommended} 匹配度: {score}% | 通勤: {commute}min | 红标: {len(record['red_flags'])}个")
        
        if not analysis.get("is_recommended", True):
            print(f"     不推荐: {analysis.get('not_recommended_reason', '')[:60]}")
        
        results.append(record)
        
        # 控制速度
        await asyncio.sleep(1)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="JD深度分析")
    parser.add_argument("--job-id", "-j", help="分析单个职位")
    parser.add_argument("--batch", "-b", action="store_true", help="批量分析")
    parser.add_argument("--min-score", "-s", type=int, default=0, help="最低匹配度")
    parser.add_argument("--filter", "-f", action="store_true", help="只看推荐职位")
    
    args = parser.parse_args()
    
    config = load_config()
    ai = AIHelper(
        provider=config.ai.provider,
        api_key=config.ai.api_key,
        model=config.ai.model,
        base_url=config.ai.base_url
    )
    user_profile = {
        "name": config.user.name,
        "experience_years": config.user.experience_years,
        "key_skills": config.user.key_skills,
        "work_summary": config.user.work_summary,
        "target_positions": config.user.target_positions
    }
    
    jobs = load_jobs()
    analysis = load_analysis()
    
    if args.job_id:
        jobs = [j for j in jobs if j["id"] == args.job_id]
    
    if not jobs:
        print("没有找到职位")
        return
    
    print("=" * 50)
    print(f"JD深度分析 | 候选人家: {config.user.home_location}")
    print(f"分析{len(jobs)}个职位")
    print("=" * 50)
    
    # 需要浏览器来抓JD
    async def run():
        browser = BrowserHelper(headless=False)
        await browser.start()
        
        try:
            await batch_analyze(jobs, ai, user_profile, args.min_score, browser)
        finally:
            await browser.close()
    
    asyncio.run(run())


if __name__ == "__main__":
    main()

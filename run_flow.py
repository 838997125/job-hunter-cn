#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
求职助手 - 一键运行完整流程
"""

import json
import os
import requests
from pathlib import Path
from datetime import datetime
import asyncio
import subprocess
import sys

# ============ 配置 ============
API_KEY = os.environ.get("DASHSCOPE_API_KEY", "your-api-key")  # 从环境变量读取，勿提交真实 key
BASE_URL = "https://coding.dashscope.aliyuncs.com/v1"
MODEL = "qwen3.5-plus"

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "resumes"
STATE_FILE = OUTPUT_DIR / "flow_state.json"

# ============ 工具函数 ============
def log(msg):
    print(msg)
    sys.stdout.flush()

def call_ai(prompt, temp=0.7):
    url = f"{BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": temp}
    resp = requests.post(url, headers=headers, json=data, timeout=120)
    if resp.status_code != 200:
        raise Exception(f"AI Error: {resp.text}")
    return resp.json()["choices"][0]["message"]["content"]

def save_state(state):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# ============ 主流程 ============
def main():
    log("=" * 60)
    log("    求职助手 - 自动化流程")
    log("=" * 60)
    
    # 步骤1: 模拟搜索职位
    log("\n[1/6] 搜索职位...")
    job = {
        "id": "boss-test-001",
        "title": "高级产品经理",
        "company": "武汉某AI科技公司",
        "salary": "20-35K",
        "location": "武汉-光谷",
        "hr": "李HR",
        "jd_text": """岗位职责：
1. 负责AI产品线的规划与落地，包括需求分析、产品设计、迭代优化
2. 协调研发、算法、运营团队，推动产品按时交付
3. 基于数据分析，持续优化产品体验和商业指标

任职要求：
1. 本科及以上学历，5年以上产品经验
2. 有AI/机器学习相关产品经验优先
3. 熟悉B端产品设计，有SaaS产品经验
4. 数据驱动思维，能独立完成数据分析"""
    }
    log(f"  找到: {job['title']} @ {job['company']}")
    log(f"  薪资: {job['salary']} | 地点: {job['location']}")
    
    # 步骤2: 分析JD
    log("\n[2/6] 分析职位描述...")
    prompt = f"""分析职位描述，提取关键信息，JSON格式输出：
{job['jd_text']}
输出: {{"position": "", "required_skills": [], "keywords": []}}"""
    
    result = call_ai(prompt)
    try:
        start, end = result.find("{"), result.rfind("}") + 1
        jd_analysis = json.loads(result[start:end])
    except:
        jd_analysis = {"position": "AI产品经理", "keywords": ["AI", "产品", "数据分析"]}
    
    log(f"  岗位: {jd_analysis.get('position', '')}")
    log(f"  关键词: {', '.join(jd_analysis.get('keywords', [])[:5])}")
    
    # 步骤3: 计算匹配度
    log("\n[3/6] 计算匹配度...")
    with open(DATA_DIR / "resume_template.json", "r", encoding="utf-8") as f:
        resume = json.load(f)
    
    summary = resume.get("basics", {}).get("summary", "")
    prompt = f"计算匹配度(0-100)。求职者: {summary[:50]}。岗位: {jd_analysis.get('position', '')}。输出JSON: {{'match_score': 85}}"
    
    result = call_ai(prompt)
    try:
        start, end = result.find("{"), result.rfind("}") + 1
        match = json.loads(result[start:end])
    except:
        match = {"match_score": 85}
    
    score = match.get("match_score", 80)
    log(f"  匹配度: {score}/100")
    
    # 步骤4: 优化简历
    log("\n[4/6] 优化简历...")
    original = resume.get("basics", {}).get("summary", "")
    prompt = f"优化简介匹配AI产品经理。原简介: {original[:80]}。关键词: {', '.join(jd_analysis.get('keywords', [])[:5])}。输出60字内优化版："
    
    new_summary = call_ai(prompt)
    resume["basics"]["summary"] = new_summary
    log(f"  新简介: {new_summary[:50]}...")
    
    # 步骤5: 生成打招呼语
    log("\n[5/6] 生成打招呼语...")
    name = resume.get("basics", {}).get("name", "")
    prompt = f"生成BOSS直聘打招呼语(50字内)。求职者: {name}, {new_summary[:30]}。岗位: {job['title']}"
    
    greeting = call_ai(prompt, temp=0.8)
    log(f"  打招呼语: {greeting}")
    
    # 步骤6: 生成文件
    log("\n[6/6] 生成简历文件...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 加载完整简历模板
    with open(DATA_DIR / "resume_template.json", "r", encoding="utf-8") as f:
        full_resume = json.load(f)
    full_resume["basics"]["summary"] = new_summary
    
    # 生成HTML
    html = generate_html(full_resume, job)
    html_path = OUTPUT_DIR / f"{name}_简历_{timestamp}.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"  HTML: {html_path}")
    
    # 生成PDF
    pdf_path = OUTPUT_DIR / f"{name}_简历_{timestamp}.pdf"
    generate_pdf(html_path, pdf_path)
    log(f"  PDF: {pdf_path}")
    
    # 保存状态
    save_state({
        "step": 6,
        "job": job,
        "jd_analysis": jd_analysis,
        "match": match,
        "greeting": greeting,
        "resume": full_resume
    })
    
    # 完成
    log("\n" + "=" * 60)
    log("    流程完成！")
    log("=" * 60)
    log(f"\n职位: {job['title']} @ {job['company']}")
    log(f"匹配度: {score}%")
    log(f"打招呼语: {greeting}")
    log(f"\n简历文件: {pdf_path}")
    
    # 打开PDF
    subprocess.run(["start", str(pdf_path)], shell=True)

def generate_html(resume, job):
    """生成完整HTML简历"""
    basics = resume.get("basics", {})
    highlights = resume.get("highlights", {})
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{basics.get('name', '')} - 产品经理简历</title>
    <style>
        body {{ font-family: "Microsoft YaHei", sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; font-size: 13px; }}
        h1 {{ text-align: center; border-bottom: 2px solid #333; font-size: 22px; }}
        h2 {{ border-bottom: 1px solid #3498db; color: #2980b9; font-size: 15px; margin-top: 20px; }}
        h3 {{ color: #34495e; font-size: 13px; margin-top: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 12px; }}
        th {{ background: #3498db; color: white; padding: 6px; }}
        td {{ border: 1px solid #ddd; padding: 6px; text-align: center; }}
        ul {{ padding-left: 18px; margin: 3px 0; }}
        li {{ margin: 3px 0; }}
        .result {{ color: #27ae60; }}
    </style>
</head>
<body>
<h1>{basics.get('name', '')}</h1>
<p style="text-align:center"><strong>{basics.get('summary', '')}</strong></p>
<p style="text-align:center">📞 {basics.get('phone', '')} | 📧 {basics.get('email', '')} | 📍 {basics.get('location', '')}</p>
<p style="text-align:center">求职意向：<strong>{job.get('title', '产品经理')}</strong></p>
<hr>
<h2>核心优势</h2>
<table><tr><th>数据驱动</th><th>AI落地</th><th>技术理解</th></tr>
<tr><td>{highlights.get('data_driven', '')}</td>
<td>{highlights.get('ai_practice', '')}</td>
<td>{highlights.get('tech_understanding', '')}</td></tr></table>
<ul>
"""
    for adv in resume.get("core_advantages", []):
        html += f"<li>{adv}</li>\n"
    
    html += "</ul><hr><h2>工作经历</h2>\n"
    
    for exp in resume.get("experience", []):
        html += f"<h3>{exp.get('company', '')} | {exp.get('title', '')} | {exp.get('period', '')}</h3>\n"
        if exp.get("summary"):
            html += f"<p style='color:#666;font-style:italic'>{exp['summary']}</p>\n"
        html += "<ul>\n"
        for h in exp.get("highlights", []):
            html += f"<li>{h}</li>\n"
        html += "</ul>\n"
        
        if exp.get("projects"):
            for i, proj in enumerate(exp["projects"], 1):
                html += f"<p><strong>项目{i}：{proj.get('name', '')}</strong></p><ul>\n"
                if proj.get("description"):
                    html += f"<li>{proj['description']}</li>\n"
                if proj.get("results"):
                    html += f"<li class='result'><strong>成果</strong>：{proj['results']}</li>\n"
                html += "</ul>\n"
    
    html += "<hr><h2>相关技能</h2>\n"
    for cat, skills in resume.get("skills", {}).items():
        html += f"<p><strong>{cat}</strong>：{', '.join(skills)}</p>\n"
    
    html += "<hr><h2>教育经历</h2>\n"
    for edu in resume.get("education", []):
        html += f"<p><strong>{edu.get('school', '')}</strong> | {edu.get('major', '')} | {edu.get('degree', '')}</p>\n"
    
    if resume.get("certifications"):
        html += "<p><strong>培训认证</strong>：" + " | ".join(resume["certifications"]) + "</p>\n"
    
    html += "</body></html>"
    return html

def generate_pdf(html_path, pdf_path):
    """生成PDF"""
    from playwright.async_api import async_playwright
    
    async def gen():
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(f"file:///{html_path}".replace("\\", "/"))
            await page.pdf(path=str(pdf_path), format="A4", margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"})
            await browser.close()
    
    asyncio.run(gen())

if __name__ == "__main__":
    main()
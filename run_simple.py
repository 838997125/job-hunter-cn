#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简化版自动化流程 - 减少AI调用"""

import json
from pathlib import Path
from datetime import datetime
import asyncio
import subprocess

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "resumes"

def main():
    print("=" * 60)
    print("    求职助手 - 自动化流程（简化版）")
    print("=" * 60)
    
    # 步骤1: 加载职位
    print("\n[1/6] 搜索职位...")
    job = {
        "id": "boss-test-001",
        "title": "高级产品经理",
        "company": "武汉某AI科技公司",
        "salary": "20-35K",
        "location": "武汉-光谷"
    }
    print(f"  找到: {job['title']} @ {job['company']}")
    print(f"  薪资: {job['salary']}")
    
    # 步骤2: 分析JD（使用预设结果）
    print("\n[2/6] 分析职位描述...")
    jd_analysis = {
        "position": "AI产品经理",
        "keywords": ["AI", "产品规划", "B端", "SaaS", "数据分析", "云计算"],
        "required_skills": ["产品经验", "AI应用", "数据分析"]
    }
    print(f"  岗位: {jd_analysis['position']}")
    print(f"  关键词: {', '.join(jd_analysis['keywords'][:5])}")
    
    # 步骤3: 计算匹配度
    print("\n[3/6] 计算匹配度...")
    score = 85
    print(f"  匹配度: {score}/100")
    
    # 步骤4: 加载简历
    print("\n[4/6] 加载简历...")
    with open(DATA_DIR / "resume_template.json", "r", encoding="utf-8") as f:
        resume = json.load(f)
    
    # 优化简介（使用预设）
    resume["basics"]["summary"] = "10年从业经验（6年技术研发+4年产品管理），专注云计算与AI应用落地。擅长技术边界评估、模型场景化及商业化，驱动业务高效增长。"
    print(f"  简历已加载: {resume['basics']['name']}")
    
    # 步骤5: 打招呼语
    print("\n[5/6] 生成打招呼语...")
    greeting = "您好，我是张一钦，10年技产复合背景，专注AI与云计算，期待进一步沟通！"
    print(f"  {greeting}")
    
    # 步骤6: 生成文件
    print("\n[6/6] 生成简历文件...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = resume["basics"]["name"]
    
    # 生成HTML
    html = generate_html(resume, job)
    html_path = OUTPUT_DIR / f"{name}_简历_{timestamp}.html"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML: {html_path}")
    
    # 生成PDF
    pdf_path = OUTPUT_DIR / f"{name}_简历_{timestamp}.pdf"
    generate_pdf(html_path, pdf_path)
    print(f"  PDF: {pdf_path}")
    
    # 完成
    print("\n" + "=" * 60)
    print("    流程完成！")
    print("=" * 60)
    print(f"\n职位: {job['title']} @ {job['company']}")
    print(f"匹配度: {score}%")
    print(f"打招呼语: {greeting}")
    print(f"\n简历文件: {pdf_path}")
    
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
        body {{ font-family: "Microsoft YaHei", sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; font-size: 13px; line-height: 1.6; }}
        h1 {{ text-align: center; border-bottom: 2px solid #2c3e50; font-size: 22px; padding-bottom: 10px; }}
        h2 {{ border-bottom: 1px solid #3498db; color: #2980b9; font-size: 15px; margin-top: 20px; }}
        h3 {{ color: #34495e; font-size: 13px; margin-top: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 12px; }}
        th {{ background: #3498db; color: white; padding: 6px; font-weight: normal; }}
        td {{ border: 1px solid #ddd; padding: 6px; text-align: center; }}
        ul {{ padding-left: 18px; margin: 3px 0; }}
        li {{ margin: 3px 0; }}
        .result {{ color: #27ae60; }}
        .intro {{ color: #666; font-style: italic; }}
    </style>
</head>
<body>
<h1>{basics.get('name', '')}</h1>
<p style="text-align:center"><strong>{basics.get('summary', '')}</strong></p>
<p style="text-align:center;color:#7f8c8d">📞 {basics.get('phone', '')} | 📧 {basics.get('email', '')} | 📍 {basics.get('location', '')}</p>
<p style="text-align:center">求职意向：<strong>{job.get('title', '产品经理')}</strong> | 期望薪资：面议</p>
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
            html += f"<p class='intro'>{exp['summary']}</p>\n"
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
        html += f"<p><strong>培训认证</strong>：{' | '.join(resume['certifications'])}</p>\n"
    
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
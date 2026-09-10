#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复简历生成 - 生成完整正确的简历"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = DATA_DIR / "resumes"

# 加载简历数据
with open(DATA_DIR / "resume_template.json", "r", encoding="utf-8") as f:
    resume = json.load(f)

# 加载优化后的简介
with open(OUTPUT_DIR / "flow_state.json", "r", encoding="utf-8") as f:
    state = json.load(f)

optimized_summary = state.get("resume", {}).get("basics", {}).get("summary", resume["basics"]["summary"])
greeting = state.get("greeting", "")

# 更新简介
resume["basics"]["summary"] = optimized_summary

def generate_full_html():
    """生成完整的HTML简历"""
    basics = resume.get("basics", {})
    highlights = resume.get("highlights", {})
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{basics.get('name', '')} - 产品经理简历</title>
    <style>
        body {{
            font-family: "Microsoft YaHei", "SimHei", sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 25px 20px;
            line-height: 1.6;
            color: #333;
            background: #fff;
            font-size: 13px;
        }}
        h1 {{
            text-align: center;
            border-bottom: 2px solid #2c3e50;
            padding-bottom: 10px;
            font-size: 22px;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        h2 {{
            border-bottom: 1px solid #3498db;
            padding-bottom: 5px;
            margin-top: 20px;
            font-size: 15px;
            color: #2980b9;
        }}
        h3 {{
            margin-top: 12px;
            margin-bottom: 5px;
            color: #34495e;
            font-size: 13px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 12px;
        }}
        th {{
            background-color: #3498db;
            color: white;
            padding: 6px;
            font-weight: normal;
        }}
        td {{
            border: 1px solid #ddd;
            padding: 6px;
            text-align: center;
        }}
        ul {{
            padding-left: 18px;
            margin: 3px 0;
        }}
        li {{
            margin: 3px 0;
        }}
        p {{
            margin: 4px 0;
        }}
        .summary {{
            text-align: center;
            font-size: 14px;
            color: #34495e;
            margin: 10px 0;
        }}
        .contact {{
            text-align: center;
            color: #7f8c8d;
            font-size: 12px;
        }}
        .result {{
            color: #27ae60;
        }}
        .section-intro {{
            color: #666;
            font-style: italic;
            margin: 5px 0;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ecf0f1;
            margin: 15px 0;
        }}
        @media print {{
            body {{ padding: 15px; font-size: 11px; }}
        }}
    </style>
</head>
<body>

<h1>{basics.get('name', '')}</h1>

<p class="summary"><strong>{basics.get('summary', '')}</strong></p>

<p class="contact">
    📞 {basics.get('phone', '')} | 📧 {basics.get('email', '')} | 📍 {basics.get('location', '')}<br>
    🔗 作品集：{basics.get('portfolio', '')} | {basics.get('availability', '')}
</p>

<p style="text-align: center;"><strong>求职意向：产品经理 | 云产品/AI产品/B端产品 | 期望薪资：面议</strong></p>

<hr>

<h2>核心优势</h2>

<table>
    <tr>
        <th>数据驱动</th>
        <th>AI落地</th>
        <th>技术理解</th>
    </tr>
    <tr>
        <td>{highlights.get('data_driven', '')}</td>
        <td>{highlights.get('ai_practice', '')}</td>
        <td>{highlights.get('tech_understanding', '')}</td>
    </tr>
</table>

<ul>
"""
    # 核心优势列表
    for adv in resume.get("core_advantages", []):
        html += f"    <li>{adv}</li>\n"
    
    html += """</ul>

<hr>

<h2>工作经历</h2>
"""
    
    # 工作经历 - 完整版
    for exp in resume.get("experience", []):
        html += f"""
<h3>{exp.get('company', '')} | {exp.get('title', '')} | {exp.get('period', '')}</h3>
"""
        if exp.get("summary"):
            html += f"""<p class="section-intro">{exp['summary']}</p>\n"""
        
        html += "<ul>\n"
        for h in exp.get("highlights", []):
            html += f"    <li>{h}</li>\n"
        html += "</ul>\n"
        
        # 项目详情
        if exp.get("projects"):
            for i, proj in enumerate(exp["projects"], 1):
                html += f"""
<p><strong>项目{i}：{proj.get('name', '')}</strong></p>
<ul>
"""
                if proj.get("description"):
                    html += f"    <li>{proj['description']}</li>\n"
                if proj.get("results"):
                    html += f"""    <li class="result"><strong>成果</strong>：{proj['results']}</li>\n"""
                html += "</ul>\n"
        
        html += "<hr>\n"
    
    # 技能
    html += """<h2>相关技能</h2>
"""
    for category, skills in resume.get("skills", {}).items():
        html += f"<p><strong>{category}</strong>：{', '.join(skills)}</p>\n"
    
    # 教育经历
    html += """
<hr>

<h2>教育培训经历</h2>
"""
    for edu in resume.get("education", []):
        html += f"""<p><strong>{edu.get('school', '')}</strong> | {edu.get('major', '')} | {edu.get('degree', '')} | {edu.get('period', '')}</p>
"""
    
    if resume.get("certifications"):
        html += """
<p><strong>培训认证</strong></p>
<ul>
"""
        for cert in resume["certifications"]:
            html += f"    <li>{cert}</li>\n"
        html += "</ul>\n"
    
    html += """
</body>
</html>"""
    
    return html

# 生成HTML
html_content = generate_full_html()

# 保存文件
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
name = resume.get("basics", {}).get("name", "简历")

html_path = OUTPUT_DIR / f"{name}_完整简历_{timestamp}.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"HTML: {html_path}")

# 生成PDF
pdf_path = OUTPUT_DIR / f"{name}_完整简历_{timestamp}.pdf"

async def gen_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file:///{html_path}".replace("\\", "/"))
        await page.pdf(
            path=str(pdf_path), 
            format="A4", 
            margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"}
        )
        await browser.close()

asyncio.run(gen_pdf())
print(f"PDF: {pdf_path}")

# 打开PDF
import subprocess
subprocess.run(["start", str(pdf_path)], shell=True)

print(f"\n打招呼语（用于BOSS直聘发送）: {greeting}")
print("\n简历已生成，不包含打招呼语！")
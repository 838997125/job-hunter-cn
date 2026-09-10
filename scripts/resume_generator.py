#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
求职助手 - 简历生成模块
支持 Markdown -> HTML -> PDF 转换
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

DATA_DIR = Path(__file__).parent.parent / "data"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = DATA_DIR / "resumes"


class ResumeGenerator:
    """简历生成器"""
    
    def __init__(self, template_path: Path = None):
        self.template_path = template_path or TEMPLATES_DIR / "resume_template.md"
        self.load_template()
    
    def load_template(self):
        """加载Markdown模板"""
        with open(self.template_path, "r", encoding="utf-8") as f:
            self.template = f.read()
    
    def generate_markdown(self, resume_data: Dict, jd_keywords: List[str] = None) -> str:
        """根据数据生成Markdown简历"""
        md = self.template
        
        # 基本信息
        basics = resume_data.get("basics", {})
        md = md.replace("{{name}}", basics.get("name", ""))
        md = md.replace("{{phone}}", basics.get("phone", ""))
        md = md.replace("{{email}}", basics.get("email", ""))
        md = md.replace("{{location}}", basics.get("location", ""))
        md = md.replace("{{portfolio}}", basics.get("portfolio", ""))
        md = md.replace("{{availability}}", basics.get("availability", ""))
        md = md.replace("{{summary}}", basics.get("summary", ""))
        
        # 核心优势
        highlights = resume_data.get("highlights", {})
        md = md.replace("{{data_driven}}", highlights.get("data_driven", ""))
        md = md.replace("{{ai_practice}}", highlights.get("ai_practice", ""))
        md = md.replace("{{tech_understanding}}", highlights.get("tech_understanding", ""))
        
        # 核心优势列表
        advantages = resume_data.get("core_advantages", [])
        adv_text = "\n".join(f"- {a}" for a in advantages)
        # 替换模板中的优势部分
        
        # 工作经历
        experiences = resume_data.get("experience", [])
        exp_sections = []
        
        for exp in experiences:
            section = f"\n### {exp.get('company', '')} | {exp.get('title', '')} | {exp.get('period', '')}\n\n"
            
            if exp.get("summary"):
                section += f"**经历总结**：{exp['summary']}\n\n"
            
            # 亮点
            for h in exp.get("highlights", []):
                section += f"- {h}\n"
            
            # 项目
            for i, proj in enumerate(exp.get("projects", []), 1):
                section += f"\n**项目{i}：{proj.get('name', '')}**\n"
                if proj.get("description"):
                    section += f"- {proj['description']}\n"
                if proj.get("results"):
                    section += f"- **成果**：{proj['results']}\n"
            
            exp_sections.append(section)
        
        # 替换工作经历部分（简化处理）
        # 实际项目中可以用更复杂的模板引擎
        
        return md
    
    def optimize_for_jd(self, resume_data: Dict, jd_keywords: List[str], 
                        jd_requirements: List[str]) -> Dict:
        """根据JD优化简历数据"""
        optimized = resume_data.copy()
        
        # 1. 优化个人简介
        summary = resume_data.get("basics", {}).get("summary", "")
        # 如果有AI模块，可以调用AI优化
        
        # 2. 调整工作经历亮点顺序（根据关键词匹配度）
        for exp in optimized.get("experience", []):
            highlights = exp.get("highlights", [])
            # 计算每条亮点与JD关键词的匹配度
            scored = []
            for h in highlights:
                score = sum(1 for kw in jd_keywords if kw.lower() in h.lower())
                scored.append((score, h))
            # 按匹配度排序
            scored.sort(key=lambda x: x[0], reverse=True)
            exp["highlights"] = [h for _, h in scored]
        
        # 3. 标记匹配的技能
        skills = resume_data.get("skills", {})
        matched_skills = {}
        for category, skill_list in skills.items():
            matched = [s for s in skill_list if any(kw.lower() in s.lower() for kw in jd_keywords)]
            if matched:
                matched_skills[category] = matched
        
        optimized["matched_skills"] = matched_skills
        
        return optimized
    
    def save_markdown(self, content: str, filename: str) -> Path:
        """保存Markdown文件"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filepath = OUTPUT_DIR / f"{filename}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath
    
    def markdown_to_html(self, md_content: str, title: str = "简历") -> str:
        """将Markdown转换为HTML"""
        # 简单的Markdown转HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: "Microsoft YaHei", "SimHei", sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }}
        h2 {{
            border-bottom: 1px solid #ccc;
            padding-bottom: 5px;
            margin-top: 30px;
        }}
        h3 {{
            margin-top: 20px;
            color: #444;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: center;
        }}
        th {{
            background-color: #f5f5f5;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin: 5px 0;
        }}
        strong {{
            color: #222;
        }}
        @media print {{
            body {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
"""
        # 转换Markdown
        lines = md_content.split("\n")
        in_list = False
        
        for line in lines:
            # 标题
            if line.startswith("# "):
                html += f"<h1>{line[2:]}</h1>\n"
            elif line.startswith("## "):
                html += f"<h2>{line[3:]}</h2>\n"
            elif line.startswith("### "):
                html += f"<h3>{line[4:]}</h3>\n"
            # 分隔线
            elif line.startswith("---"):
                html += "<hr>\n"
            # 列表
            elif line.startswith("- "):
                if not in_list:
                    html += "<ul>\n"
                    in_list = True
                html += f"<li>{line[2:]}</li>\n"
            else:
                if in_list and not line.startswith("-"):
                    html += "</ul>\n"
                    in_list = False
                # 普通段落
                if line.strip():
                    # 处理粗体
                    line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                    html += f"<p>{line}</p>\n"
        
        if in_list:
            html += "</ul>\n"
        
        html += "</body>\n</html>"
        return html
    
    def save_html(self, html_content: str, filename: str) -> Path:
        """保存HTML文件"""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        filepath = OUTPUT_DIR / f"{filename}.html"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        return filepath


def check_pdf_dependencies():
    """检查PDF转换依赖"""
    dependencies = {
        "weasyprint": False,
        "pdfkit": False,
        "markdown": False
    }
    
    try:
        import weasyprint
        dependencies["weasyprint"] = True
    except ImportError:
        pass
    
    try:
        import pdfkit
        dependencies["pdfkit"] = True
    except ImportError:
        pass
    
    try:
        import markdown
        dependencies["markdown"] = True
    except ImportError:
        pass
    
    return dependencies


def html_to_pdf_weasyprint(html_content: str, output_path: Path) -> bool:
    """使用WeasyPrint将HTML转换为PDF"""
    try:
        from weasyprint import HTML
        HTML(string=html_content).write_pdf(output_path)
        return True
    except Exception as e:
        print(f"WeasyPrint转换失败: {e}")
        return False


def html_to_pdf_pdfkit(html_content: str, output_path: Path) -> bool:
    """使用pdfkit将HTML转换为PDF"""
    try:
        import pdfkit
        import tempfile
        
        # 先保存HTML到临时文件
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            temp_html = f.name
        
        options = {
            'encoding': 'UTF-8',
            'quiet': ''
        }
        pdfkit.from_file(temp_html, str(output_path), options=options)
        return True
    except Exception as e:
        print(f"pdfkit转换失败: {e}")
        return False


def html_to_pdf_playwright(html_content: str, output_path: Path) -> bool:
    """使用Playwright将HTML转换为PDF"""
    try:
        import asyncio
        from playwright.async_api import async_playwright
        import tempfile
        
        async def convert():
            # 保存HTML到临时文件
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_html = f.name
            
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.goto(f'file://{temp_html}')
                await page.pdf(path=str(output_path), format='A4')
                await browser.close()
        
        asyncio.run(convert())
        return True
    except Exception as e:
        print(f"Playwright转换失败: {e}")
        return False


def generate_pdf(html_content: str, output_path: Path) -> bool:
    """尝试多种方式生成PDF"""
    # 方式1: WeasyPrint (纯Python，但Windows依赖复杂)
    # 方式2: pdfkit (需要wkhtmltopdf)
    # 方式3: Playwright (已安装)
    
    # 优先使用Playwright
    if html_to_pdf_playwright(html_content, output_path):
        return True
    
    # 备选方案
    if html_to_pdf_weasyprint(html_content, output_path):
        return True
    
    if html_to_pdf_pdfkit(html_content, output_path):
        return True
    
    return False


# 测试
if __name__ == "__main__":
    # 检查依赖
    deps = check_pdf_dependencies()
    print("PDF转换依赖检查:")
    for name, available in deps.items():
        status = "✓ 已安装" if available else "✗ 未安装"
        print(f"  {name}: {status}")
    
    # 加载简历数据
    resume_path = DATA_DIR / "resume_template.json"
    if resume_path.exists():
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_data = json.load(f)
        
        # 生成Markdown
        generator = ResumeGenerator()
        md_content = generator.generate_markdown(resume_data)
        
        # 保存Markdown
        md_path = generator.save_markdown(md_content, "test_resume")
        print(f"\nMarkdown已保存: {md_path}")
        
        # 转换为HTML
        html_content = generator.markdown_to_html(md_content)
        html_path = generator.save_html(html_content, "test_resume")
        print(f"HTML已保存: {html_path}")
        
        # 转换为PDF
        pdf_path = OUTPUT_DIR / "test_resume.pdf"
        if generate_pdf(html_content, pdf_path):
            print(f"PDF已保存: {pdf_path}")
        else:
            print("PDF转换失败，请安装依赖: pip install weasyprint 或 pip install pdfkit")
            print("或确保已安装 playwright: playwright install chromium")
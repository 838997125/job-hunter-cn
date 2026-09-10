#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
求职助手 - 简历优化模块
根据JD自动调整简历内容
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from utils.ai_helper import AIHelper


DATA_DIR = Path(__file__).parent.parent / "data"
RESUME_TEMPLATE = DATA_DIR / "resume_template.json"
JD_ANALYSIS_FILE = DATA_DIR / "jd_analysis.json"
OPTIMIZED_DIR = DATA_DIR / "resumes"


def load_resume_template() -> Dict:
    """加载简历模板"""
    if RESUME_TEMPLATE.exists():
        with open(RESUME_TEMPLATE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_jd_analysis(job_id: str = None) -> Dict:
    """加载JD分析结果"""
    if JD_ANALYSIS_FILE.exists():
        with open(JD_ANALYSIS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if job_id:
                return data.get(job_id, {})
            return data
    return {}


def save_optimized_resume(resume: Dict, job_id: str, job_title: str):
    """保存优化后的简历"""
    OPTIMIZED_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    safe_title = job_title.replace("/", "-").replace("\\", "-")[:20]
    filename = f"resume_{job_id}_{safe_title}.json"
    filepath = OPTIMIZED_DIR / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(resume, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 简历已保存: {filepath}")
    return filepath


class ResumeOptimizer:
    """简历优化器"""
    
    def __init__(self, ai: AIHelper, user_config):
        self.ai = ai
        self.user_config = user_config
    
    def optimize_summary(self, resume: Dict, jd_keywords: List[str], 
                         jd_requirements: List[str]) -> str:
        """优化个人简介"""
        original = resume.get("basics", {}).get("summary", "")
        
        prompt = f"""请优化以下求职者的个人简介，使其更匹配目标岗位。

原始简介：
{original}

目标岗位关键词：{', '.join(jd_keywords[:10])}
岗位核心要求：{', '.join(jd_requirements[:5])}

优化要求：
1. 保持真实，不编造经历
2. 突出与岗位匹配的技能和经验
3. 控制在80-120字
4. 使用数据化表达
5. 体现独特价值

直接输出优化后的简介："""
        
        return self.ai.chat([{"role": "user", "content": prompt}], temperature=0.7)
    
    def optimize_experience(self, resume: Dict, jd_keywords: List[str],
                           jd_requirements: List[str]) -> List[Dict]:
        """优化工作经历"""
        experiences = resume.get("experience", [])
        optimized = []
        
        for exp in experiences:
            highlights = exp.get("highlights", [])
            
            # 让AI优化每条亮点
            prompt = f"""请优化以下工作经历亮点，使其更匹配目标岗位。

公司：{exp.get('company', '')}
职位：{exp.get('title', '')}
原始亮点：
{chr(10).join(f'- {h}' for h in highlights)}

目标岗位关键词：{', '.join(jd_keywords[:10])}
岗位核心要求：{', '.join(jd_requirements[:5])}

优化要求：
1. 保持真实，不编造
2. 嵌入相关关键词
3. 用数据说话（数字、百分比、金额）
4. 每条控制在20-30字
5. 突出成果而非过程
6. 返回4-5条亮点

请以JSON数组格式输出优化后的亮点：
["亮点1", "亮点2", "亮点3", "亮点4"]"""
            
            try:
                result = self.ai.chat([{"role": "user", "content": prompt}], temperature=0.7)
                # 提取JSON数组
                start = result.find("[")
                end = result.rfind("]") + 1
                new_highlights = json.loads(result[start:end])
                
                optimized_exp = exp.copy()
                optimized_exp["highlights"] = new_highlights
                optimized_exp["optimized"] = True
                optimized.append(optimized_exp)
                
            except Exception as e:
                print(f"   优化失败: {e}")
                optimized.append(exp)
        
        return optimized
    
    def optimize_skills(self, resume: Dict, jd_keywords: List[str]) -> Dict:
        """优化技能部分 - 调整顺序和重点"""
        skills = resume.get("skills", {})
        
        # 将JD关键词与技能匹配
        all_skills = []
        for category, skill_list in skills.items():
            all_skills.extend(skill_list)
        
        # 计算每个技能与JD的匹配度
        matched_skills = []
        for skill in all_skills:
            for keyword in jd_keywords:
                if keyword.lower() in skill.lower() or skill.lower() in keyword.lower():
                    matched_skills.append(skill)
                    break
        
        # 重新组织技能
        optimized = {
            "核心技能（匹配岗位）": list(set(matched_skills))[:8],
            **skills
        }
        
        return optimized
    
    def generate_cover_letter(self, resume: Dict, jd_info: Dict, 
                              company: str, position: str) -> str:
        """生成求职信"""
        prompt = f"""请根据以下信息生成一封求职信。

求职者信息：
- 姓名：{resume.get('basics', {}).get('name', '')}
- 简介：{resume.get('basics', {}).get('summary', '')}
- 核心技能：{list(resume.get('skills', {}).keys())}

目标岗位：
- 公司：{company}
- 职位：{position}
- 要求：{jd_info.get('jd_analysis', {}).get('key_responsibilities', [])[:3]}

要求：
1. 简洁有力，不超过300字
2. 突出匹配点
3. 表达求职意向和热情
4. 避免客套话

直接输出求职信："""
        
        return self.ai.chat([{"role": "user", "content": prompt}], temperature=0.8)
    
    def optimize_for_jd(self, resume: Dict, jd_analysis: Dict, 
                        job_title: str, company: str) -> Dict:
        """根据JD优化完整简历"""
        print(f"\n{'='*50}")
        print(f"开始优化简历: {job_title} - {company}")
        print(f"{'='*50}")
        
        jd_data = jd_analysis.get("jd_analysis", {})
        jd_keywords = jd_data.get("keywords", []) + jd_data.get("required_skills", [])
        jd_requirements = jd_data.get("key_responsibilities", [])
        
        optimized = resume.copy()
        
        # 1. 优化个人简介
        print("\n[1/4] 优化个人简介...")
        try:
            optimized["basics"]["summary"] = self.optimize_summary(
                resume, jd_keywords, jd_requirements
            )
            print("✓ 个人简介已优化")
        except Exception as e:
            print(f"✗ 个人简介优化失败: {e}")
        
        # 2. 优化工作经历
        print("\n[2/4] 优化工作经历...")
        try:
            optimized["experience"] = self.optimize_experience(
                resume, jd_keywords, jd_requirements
            )
            print("✓ 工作经历已优化")
        except Exception as e:
            print(f"✗ 工作经历优化失败: {e}")
        
        # 3. 优化技能
        print("\n[3/4] 优化技能展示...")
        try:
            optimized["skills"] = self.optimize_skills(resume, jd_keywords)
            print("✓ 技能展示已优化")
        except Exception as e:
            print(f"✗ 技能优化失败: {e}")
        
        # 4. 生成求职信
        print("\n[4/4] 生成求职信...")
        try:
            optimized["cover_letter"] = self.generate_cover_letter(
                resume, jd_analysis, company, job_title
            )
            print("✓ 求职信已生成")
        except Exception as e:
            print(f"✗ 求职信生成失败: {e}")
        
        # 添加元数据
        optimized["_meta"] = {
            "optimized_at": datetime.now().isoformat(),
            "target_job": job_title,
            "target_company": company,
            "match_score": jd_analysis.get("match_result", {}).get("match_score", 0)
        }
        
        return optimized


def main():
    parser = argparse.ArgumentParser(description="简历优化")
    parser.add_argument("--job-id", "-j", help="目标职位ID")
    parser.add_argument("--all", "-a", action="store_true", help="优化所有已分析的职位")
    parser.add_argument("--preview", "-p", action="store_true", help="预览优化结果（不保存）")
    parser.add_argument("--cover-letter", "-c", action="store_true", help="仅生成求职信")
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 初始化AI
    ai = AIHelper(
        provider=config.ai.provider,
        api_key=config.ai.api_key,
        model=config.ai.model,
        base_url=config.ai.base_url
    )
    
    # 加载简历模板
    resume = load_resume_template()
    if not resume:
        print("❌ 未找到简历模板，请先创建 data/resume_template.json")
        return
    
    # 初始化优化器
    optimizer = ResumeOptimizer(ai, config)
    
    if args.job_id:
        # 优化单个职位
        jd_analysis = load_jd_analysis(args.job_id)
        if not jd_analysis:
            print(f"❌ 未找到职位分析: {args.job_id}")
            print("提示：请先运行 jd_analyzer.py 分析该职位")
            return
        
        job_title = jd_analysis.get("title", "未知职位")
        company = jd_analysis.get("company", "未知公司")
        
        optimized = optimizer.optimize_for_jd(resume, jd_analysis, job_title, company)
        
        if not args.preview:
            save_optimized_resume(optimized, args.job_id, job_title)
        
        # 预览
        print("\n" + "="*50)
        print("优化后的个人简介：")
        print("="*50)
        print(optimized.get("basics", {}).get("summary", ""))
        
        print("\n" + "="*50)
        print("优化后的工作经历（最近一份）：")
        print("="*50)
        exp = optimized.get("experience", [{}])[0]
        print(f"{exp.get('company', '')} - {exp.get('title', '')}")
        for h in exp.get("highlights", []):
            print(f"  • {h}")
        
        if optimized.get("cover_letter"):
            print("\n" + "="*50)
            print("求职信：")
            print("="*50)
            print(optimized["cover_letter"])
    
    elif args.all:
        # 批量优化
        all_analysis = load_jd_analysis()
        if not all_analysis:
            print("❌ 没有已分析的职位")
            return
        
        print(f"找到 {len(all_analysis)} 个已分析的职位")
        
        for job_id, jd_analysis in all_analysis.items():
            job_title = jd_analysis.get("title", "未知职位")
            company = jd_analysis.get("company", "未知公司")
            
            optimized = optimizer.optimize_for_jd(resume, jd_analysis, job_title, company)
            save_optimized_resume(optimized, job_id, job_title)
            
            print()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
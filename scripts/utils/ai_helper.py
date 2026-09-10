#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
求职助手 - AI辅助模块
支持通义千问、OpenAI、DeepSeek
"""

import json
import requests
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class AIProvider:
    """AI提供商配置"""
    name: str
    base_url: str
    model: str


# 支持的AI提供商
PROVIDERS = {
    "dashscope": AIProvider(
        name="通义千问",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-plus"
    ),
    "openai": AIProvider(
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini"
    ),
    "deepseek": AIProvider(
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat"
    ),
    "minimax": AIProvider(
        name="MiniMax",
        base_url="https://api.minimax.chat/v1",
        model="MiniMax-M2.7"
    ),
    "minimax_native": AIProvider(
        name="MiniMax",
        base_url="https://api.minimax.chat/v1/text",
        model="MiniMax-M2.7"
    )
}


class AIHelper:
    """AI辅助类"""
    
    def __init__(self, provider: str = "dashscope", api_key: str = "", model: str = "", base_url: str = ""):
        self.provider = PROVIDERS.get(provider, PROVIDERS["dashscope"])
        self.api_key = api_key
        self.model = model or self.provider.model
        self.base_url = base_url or self.provider.base_url

    def chat(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """调用AI对话"""
        if not self.api_key:
            raise ValueError("API Key未配置")

        # MiniMax 走原生端点
        if self.provider.name == "MiniMax":
            url = f"{self.base_url}/chatcompletion_v2"
        else:
            url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }

        response = requests.post(url, headers=headers, json=data, timeout=60)

        if response.status_code != 200:
            raise Exception(f"AI调用失败: {response.text}")

        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def analyze_jd(self, jd_text: str, user_skills: List[str] = None) -> Dict:
        """分析职位描述"""
        prompt = f"""你是一个专业的HR，请分析以下职位描述，提取关键信息：

职位描述：
{jd_text}

请以JSON格式输出：
{{
    "position": "岗位名称",
    "company": "公司名称",
    "required_skills": ["技能1", "技能2"],
    "preferred_skills": ["加分项1"],
    "experience_years": "年限要求",
    "education": "学历要求",
    "salary_range": "薪资范围",
    "key_responsibilities": ["职责1", "职责2"],
    "keywords": ["关键词1", "关键词2"]
}}"""
        
        result = self.chat([{"role": "user", "content": prompt}])
        
        try:
            # 提取JSON
            start = result.find("{")
            end = result.rfind("}") + 1
            return json.loads(result[start:end])
        except:
            return {"raw": result}
    
    def calculate_match_score(self, jd_analysis: Dict, user_profile: Dict) -> Dict:
        """计算匹配度"""
        prompt = f"""请根据职位要求与求职者背景，计算匹配度评分：

职位要求：
{json.dumps(jd_analysis, ensure_ascii=False, indent=2)}

求职者背景：
{json.dumps(user_profile, ensure_ascii=False, indent=2)}

请输出JSON：
{{
    "match_score": 85,
    "matched_skills": ["匹配的技能"],
    "missing_skills": ["缺失的技能"],
    "suggestions": ["改进建议"],
    "highlights": ["可突出的亮点"]
}}"""
        
        result = self.chat([{"role": "user", "content": prompt}])
        
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            return json.loads(result[start:end])
        except:
            return {"raw": result}
    
    def generate_greeting(self, job_info: Dict, user_profile: Dict) -> str:
        """生成打招呼语"""
        prompt = f"""你是一个求职者，需要给HR发送简短的打招呼语。

岗位信息：
- 岗位：{job_info.get('position', '未知')}
- 公司：{job_info.get('company', '未知')}
- 要求：{', '.join(job_info.get('required_skills', [])[:5])}

求职者信息：
- 姓名：{user_profile.get('name', '求职者')}
- 经验：{user_profile.get('experience_years', 0)}年
- 核心技能：{', '.join(user_profile.get('key_skills', [])[:5])}
- 一句话介绍：{user_profile.get('work_summary', '')}

要求：
1. 简洁有力，不超过100字
2. 突出匹配点
3. 表达求职意向
4. 不要太客套

直接输出打招呼语，不要其他内容："""
        
        return self.chat([{"role": "user", "content": prompt}], temperature=0.8)
    
    def optimize_resume_section(self, section_name: str, section_content: str,
                                 jd_keywords: List[str]) -> str:
        """优化简历某一部分"""
        prompt = f"""请优化以下简历内容，使其更匹配目标岗位：

目标岗位关键词：{', '.join(jd_keywords)}

原始{section_name}：
{section_content}

优化要求：
1. 保留核心信息
2. 嵌入相关关键词
3. 用数据说话
4. 突出成果

直接输出优化后的内容："""

        return self.chat([{"role": "user", "content": prompt}])

    def optimize_resume_for_jd(self, resume: Dict, jd_analysis: Dict) -> Dict:
        """根据JD优化整个简历"""
        prompt = f"""你是一个专业的简历优化专家。请根据目标岗位要求，优化求职者的简历。

## 目标岗位信息
- 岗位：{jd_analysis.get('position', '未知')}
- 公司：{jd_analysis.get('company', '未知')}
- 必需技能：{', '.join(jd_analysis.get('required_skills', []))}
- 加分技能：{', '.join(jd_analysis.get('preferred_skills', []))}
- 经验要求：{jd_analysis.get('experience_years', '不限')}
- 学历要求：{jd_analysis.get('education', '不限')}
- 核心职责：{', '.join(jd_analysis.get('key_responsibilities', []))}

## 求职者原始简历
{json.dumps(resume, ensure_ascii=False, indent=2)}

## 优化要求
1. **个人简介优化**：根据岗位特点，调整个人简介，突出匹配点
2. **工作经历优化**：
   - 调整描述顺序，把最相关的内容放前面
   - 嵌入JD关键词（自然融入，不要生硬堆砌）
   - 用具体数据强化成果描述
3. **技能标签优化**：根据JD要求，重新排序技能，突出匹配技能
4. **项目经历优化**：选择最匹配的项目，调整描述重点

请以JSON格式输出优化后的简历：
{{
    "optimized_summary": "优化后的个人简介",
    "optimized_experience": [
        {{
            "company": "公司名",
            "title": "职位",
            "period": "时间",
            "highlights": ["优化后的工作成果1", "优化后的工作成果2"]
        }}
    ],
    "optimized_skills": {{
        "技能分类": ["技能1", "技能2"]
    }},
    "optimized_projects": [
        {{
            "name": "项目名",
            "role": "角色",
            "description": "优化后的描述",
            "results": ["成果1", "成果2"]
        }}
    ],
    "optimization_notes": ["优化说明1", "优化说明2"]
}}"""

        result = self.chat([{"role": "user", "content": prompt}], temperature=0.7)

        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            return json.loads(result[start:end])
        except:
            return {"raw": result, "error": "JSON解析失败"}

    def generate_cover_letter(self, job_info: Dict, user_profile: Dict, resume: Dict) -> str:
        """生成求职信"""
        prompt = f"""请根据以下信息生成一封求职信。

## 目标岗位
- 岗位：{job_info.get('position', '')}
- 公司：{job_info.get('company', '')}
- 要求：{', '.join(job_info.get('required_skills', [])[:5])}

## 求职者信息
- 姓名：{user_profile.get('name', '')}
- 经验：{user_profile.get('experience_years', 0)}年
- 核心技能：{', '.join(user_profile.get('key_skills', [])[:5])}
- 简介：{user_profile.get('work_summary', '')}

## 工作经历摘要
{json.dumps(resume.get('experience', [])[:2], ensure_ascii=False, indent=2)}

## 要求
1. 格式：标准求职信格式
2. 长度：300-500字
3. 风格：专业但不刻板，真诚有温度
4. 内容：
   - 说明应聘岗位
   - 突出与岗位的匹配点
   - 表达对公司的了解和兴趣
   - 展示核心价值
   - 表达面试意愿

直接输出求职信正文："""

        return self.chat([{"role": "user", "content": prompt}], temperature=0.8)


# 测试
if __name__ == "__main__":
    # 示例用法
    ai = AIHelper(provider="dashscope", api_key="your-api-key")
    
    jd = """
    职位：高级产品经理
    公司：某科技公司
    要求：
    - 5年以上产品经验
    - 有B端产品经验
    - 熟悉云计算/AI领域
    - 数据驱动决策能力
    """
    
    # result = ai.analyze_jd(jd)
    # print(result)
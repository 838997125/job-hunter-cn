#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
求职助手 - 配置管理模块
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict

# 获取技能目录路径
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
CONFIG_FILE = DATA_DIR / "user_config.json"


@dataclass
class UserConfig:
    """用户配置"""
    name: str = ""
    phone: str = ""
    email: str = ""
    resume_path: str = ""
    target_positions: List[str] = None
    target_cities: List[str] = None
    home_location: str = ""           # 家庭住址（用于通勤计算）
    commute_preference: str = ""       # 通勤偏好说明
    salary_range: str = ""
    experience_years: int = 0
    
    # 工作经历摘要（用于生成打招呼语）
    work_summary: str = ""
    key_skills: List[str] = None
    
    def __post_init__(self):
        if self.target_positions is None:
            self.target_positions = []
        if self.target_cities is None:
            self.target_cities = []
        if self.key_skills is None:
            self.key_skills = []


@dataclass
class AIConfig:
    """AI配置"""
    provider: str = "dashscope"  # dashscope, openai, deepseek
    model: str = "qwen-plus"
    api_key: str = ""
    base_url: str = ""


@dataclass
class BrowserConfig:
    """浏览器配置"""
    headless: bool = False
    timeout: int = 30
    user_data_dir: str = ""


@dataclass
class AppConfig:
    """应用配置"""
    user: UserConfig = None
    ai: AIConfig = None
    browser: BrowserConfig = None
    
    def __post_init__(self):
        if self.user is None:
            self.user = UserConfig()
        if self.ai is None:
            self.ai = AIConfig()
        if self.browser is None:
            self.browser = BrowserConfig()


def load_config() -> AppConfig:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        user = UserConfig(**data.get("user", {}))
        ai = AIConfig(**data.get("ai", {}))
        browser = BrowserConfig(**data.get("browser", {}))
        
        return AppConfig(user=user, ai=ai, browser=browser)
    
    return AppConfig()


def save_config(config: AppConfig):
    """保存配置文件"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    data = {
        "user": asdict(config.user),
        "ai": asdict(config.ai),
        "browser": asdict(config.browser)
    }
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def setup_config():
    """交互式配置"""
    print("=" * 50)
    print("求职助手 - 配置向导")
    print("=" * 50)
    
    config = load_config()
    
    # 用户信息
    print("\n【基本信息】")
    config.user.name = input(f"姓名 [{config.user.name}]: ") or config.user.name
    config.user.phone = input(f"手机号 [{config.user.phone}]: ") or config.user.phone
    config.user.email = input(f"邮箱 [{config.user.email}]: ") or config.user.email
    
    # 简历路径
    print("\n【简历路径】")
    resume_input = input(f"简历文件路径 [{config.user.resume_path}]: ")
    if resume_input:
        config.user.resume_path = os.path.expanduser(resume_input)
    
    # 求职意向
    print("\n【求职意向】")
    positions_input = input(f"目标岗位（逗号分隔）[{','.join(config.user.target_positions or [])}]: ")
    if positions_input:
        config.user.target_positions = [p.strip() for p in positions_input.split(",")]
    
    cities_input = input(f"目标城市（逗号分隔）[{','.join(config.user.target_cities or [])}]: ")
    if cities_input:
        config.user.target_cities = [c.strip() for c in cities_input.split(",")]
    
    config.user.salary_range = input(f"期望薪资 [{config.user.salary_range}]: ") or config.user.salary_range
    exp_input = input(f"工作年限 [{config.user.experience_years}]: ")
    if exp_input:
        config.user.experience_years = int(exp_input)
    
    # 工作摘要
    print("\n【工作摘要】（用于生成打招呼语）")
    config.user.work_summary = input(f"一句话介绍 [{config.user.work_summary}]: ") or config.user.work_summary
    
    skills_input = input(f"核心技能（逗号分隔）[{','.join(config.user.key_skills or [])}]: ")
    if skills_input:
        config.user.key_skills = [s.strip() for s in skills_input.split(",")]
    
    # AI配置
    print("\n【AI配置】")
    config.ai.provider = input(f"AI提供商 (dashscope/openai/deepseek) [{config.ai.provider}]: ") or config.ai.provider
    config.ai.model = input(f"模型名称 [{config.ai.model}]: ") or config.ai.model
    config.ai.api_key = input(f"API Key [{config.ai.api_key[:8] + '...' if config.ai.api_key else ''}]: ") or config.ai.api_key
    
    # 保存配置
    save_config(config)
    print("\n✅ 配置已保存到:", CONFIG_FILE)
    
    return config


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="求职助手配置管理")
    parser.add_argument("--setup", action="store_true", help="交互式配置")
    parser.add_argument("--show", action="store_true", help="显示当前配置")
    
    args = parser.parse_args()
    
    if args.setup:
        setup_config()
    elif args.show:
        config = load_config()
        print(json.dumps(asdict(config), ensure_ascii=False, indent=2))
    else:
        parser.print_help()
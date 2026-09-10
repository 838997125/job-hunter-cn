#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
求职助手 - 浏览器自动化工具
基于 Playwright 实现
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, Browser


@dataclass
class JobInfo:
    """职位信息"""
    id: str
    title: str
    company: str
    salary: str
    location: str
    experience: str
    education: str
    jd_url: str
    jd_text: str = ""
    hr_name: str = ""
    hr_status: str = ""


class BrowserHelper:
    """浏览器自动化工具类"""
    
    def __init__(self, headless: bool = False, user_data_dir: str = ""):
        self.headless = headless
        self.user_data_dir = user_data_dir or "./data/browser_profile"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def start(self):
        """启动浏览器（使用持久化目录，复用登录态）"""
        self.playwright = await async_playwright().start()
        # 使用持久化上下文，自动保存登录Cookie
        self.context = await self.playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled'],
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.browser = None  # 持久上下文不需要browser引用
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def goto(self, url: str, wait_until: str = "domcontentloaded"):
        """导航到页面"""
        await self.page.goto(url, wait_until=wait_until, timeout=60000)
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000):
        """等待元素出现"""
        await self.page.wait_for_selector(selector, timeout=timeout)
    
    async def click(self, selector: str):
        """点击元素"""
        await self.page.click(selector)
    
    async def fill(self, selector: str, text: str):
        """填充输入框"""
        await self.page.fill(selector, text)
    
    async def get_text(self, selector: str) -> str:
        """获取元素文本"""
        element = await self.page.query_selector(selector)
        if element:
            return await element.inner_text()
        return ""
    
    async def screenshot(self, path: str):
        """截图"""
        await self.page.screenshot(path=path)


class BossZhipinClient:
    """BOSS直聘客户端"""
    
    BASE_URL = "https://www.zhipin.com"
    
    def __init__(self, browser: BrowserHelper):
        self.browser = browser
        self.logged_in = False
    
    async def login_qrcode(self):
        """扫码登录"""
        await self.browser.goto(f"{self.BASE_URL}/web/user/")
        
        # 等待用户扫码
        print("请在浏览器中扫描二维码登录...")
        
        # 检测登录成功（URL变化或出现用户头像）
        try:
            await self.browser.page.wait_for_url("**/web/geek/**", timeout=120000)
            self.logged_in = True
            print("✅ 登录成功！")
            return True
        except:
            print("❌ 登录超时")
            return False
    
    async def search_jobs(self, keyword: str, city: str = "武汉", 
                          page: int = 1) -> List[JobInfo]:
        """搜索职位"""
        # 武汉的城市编码
        city_codes = {"武汉": "101200100", "北京": "101010100", "上海": "101020100"}
        city_code = city_codes.get(city, "101200100")
        
        url = f"{self.BASE_URL}/web/geek/job?query={keyword}&city={city_code}&page={page}"
        await self.browser.goto(url, wait_until="domcontentloaded")
        
        # 等待职位卡片出现
        try:
            await self.browser.page.wait_for_selector(".job-card-box", timeout=15000)
        except:
            print("⚠️ 等待职位列表超时，继续尝试解析...")
        
        await asyncio.sleep(2)
        
        jobs = []
        
        # 获取职位卡片（选择器需要根据实际页面调整）
        job_cards = await self.browser.page.query_selector_all(".job-card-box")
        
        for card in job_cards:
            try:
                # 提取职位信息
                title = await card.query_selector(".job-name")
                title_text = await title.inner_text() if title else ""
                
                salary = await card.query_selector(".job-salary")
                salary_text = await salary.inner_text() if salary else ""
                
                company = await card.query_selector(".boss-name")
                company_text = await company.inner_text() if company else ""
                
                location = await card.query_selector(".company-location")
                location_text = await location.inner_text() if location else ""
                
                # 获取职位链接
                link = await card.query_selector("a.job-name")
                href = await link.get_attribute("href") if link else ""
                
                # 提取职位ID
                job_id = href.split("/")[-1].split(".")[0] if href else ""
                
                job = JobInfo(
                    id=job_id,
                    title=title_text,
                    company=company_text,
                    salary=salary_text,
                    location=location_text,
                    experience="",
                    education="",
                    jd_url=f"{self.BASE_URL}{href}" if href else ""
                )
                jobs.append(job)
                
            except Exception as e:
                print(f"解析职位卡片失败: {e}")
                continue
        
        return jobs
    
    async def get_job_detail(self, job_id: str) -> Dict:
        """获取职位详情"""
        # 注意：job_id 来自 jobs.json 中的 id 字段
        url = f"{self.BASE_URL}/job_detail/{job_id}.html"
        await self.browser.goto(url)
        
        await asyncio.sleep(2)
        
        # 获取职位描述
        jd_el = await self.browser.page.query_selector(".job-sec-text")
        jd_text = await jd_el.inner_text() if jd_el else ""
        
        # 获取HR信息
        hr_el = await self.browser.page.query_selector(".job-detail .name")
        hr_name = await hr_el.inner_text() if hr_el else ""
        
        return {
            "jd_text": jd_text,
            "hr_name": hr_name
        }
    
    async def apply_job(self, job_id: str, greeting: str = "", resume_path: str = "") -> bool:
        """投递职位
        
        Args:
            job_id: 职位ID
            greeting: 打招呼语（可选）
            resume_path: 简历文件路径（可选）
        """
        # 正确URL格式
        url = f"{self.BASE_URL}/job_detail/{job_id}.html"
        await self.browser.goto(url)
        
        await asyncio.sleep(2)
        
        try:
            # 点击"立即沟通"按钮（会触发跳转到聊天页）
            apply_btn = await self.browser.page.query_selector(".btn-startchat")
            if not apply_btn:
                print(f"⚠️ 未找到沟通按钮: {job_id}")
                return False
            
            await apply_btn.click()
            
            # 等待跳转到聊天页面或URL变化
            try:
                await self.browser.page.wait_for_url("**/web/geek/chat**", timeout=15000)
            except:
                # URL没变也继续，可能是侧边栏模式
                pass
            await asyncio.sleep(2)
            
            # 上传简历（如果有）
            if resume_path:
                file_input = await self.browser.page.query_selector(".upload-resume__old input[type=file]")
                if file_input:
                    await file_input.set_input_files(resume_path)
                    await asyncio.sleep(2)
                    print(f"📎 简历已附加")
            
            # 填写打招呼语
            if greeting:
                textarea = await self.browser.page.query_selector("textarea")
                if textarea:
                    await textarea.fill(greeting)
                    await asyncio.sleep(0.5)
            
            # 点击发送按钮
            send_btn = await self.browser.page.query_selector("[class*=send]")
            if send_btn:
                await send_btn.click(force=True)
                await asyncio.sleep(1)
                print(f"✅ 已投递: {job_id}")
                return True
            else:
                print(f"⚠️ 未找到发送按钮: {job_id}")
                return False
                
        except Exception as e:
            print(f"❌ 投递失败: {e}")
            return False


class LiepinClient:
    """猎聘客户端"""
    
    BASE_URL = "https://www.liepin.com"
    
    def __init__(self, browser: BrowserHelper):
        self.browser = browser
    
    async def search_jobs(self, keyword: str, city: str = "武汉") -> List[JobInfo]:
        """搜索职位 - 猎聘"""
        # TODO: 实现猎聘搜索
        return []


# 同步包装函数
def run_async(coro):
    """运行异步函数"""
    return asyncio.get_event_loop().run_until_complete(coro)


if __name__ == "__main__":
    # 测试代码
    async def test():
        browser = BrowserHelper(headless=False)
        await browser.start()
        
        client = BossZhipinClient(browser)
        
        # 扫码登录
        await client.login_qrcode()
        
        # 搜索职位
        jobs = await client.search_jobs("产品经理", "武汉")
        for job in jobs[:5]:
            print(f"{job.title} - {job.company} - {job.salary}")
        
        await browser.close()
    
    run_async(test())
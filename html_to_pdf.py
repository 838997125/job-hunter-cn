#!/usr/bin/env python3
"""HTML转PDF - 使用纯Playwright"""
import asyncio, sys
from pathlib import Path

async def html_to_pdf(html_path: str, pdf_path: str):
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = Path(html_path).resolve().as_uri()
        print(f"打开: {url}")
        await page.goto(url)
        await asyncio.sleep(2)
        
        await page.pdf(path=pdf_path, format='A4', print_background=True, margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"})
        print(f"PDF已生成: {pdf_path}")
        
        await browser.close()

if __name__ == "__main__":
    html_file = Path(__file__).parent / "data" / "resumes" / "张一钦_完整简历_20260327_135252.html"
    pdf_file = Path(__file__).parent / "data" / "resumes" / "张一钦_完整简历_20260327_135252_v3.pdf"

    asyncio.run(html_to_pdf(str(html_file), str(pdf_file)))

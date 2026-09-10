import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

html_path = Path(r"C:\Users\HUAWEI\.openclaw\workspace\skills\job-hunter-cn\data\resumes\张一钦-产品经理-优化版.html")
pdf_path = Path(r"C:\Users\HUAWEI\.openclaw\workspace\skills\job-hunter-cn\data\resumes\张一钦-产品经理-优化版.pdf")

async def gen_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file:///{html_path}".replace("\\", "/"))
        await page.pdf(
            path=str(pdf_path), 
            format="A4", 
            margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"}
        )
        await browser.close()
    print(f"PDF generated: {pdf_path}")

asyncio.run(gen_pdf())
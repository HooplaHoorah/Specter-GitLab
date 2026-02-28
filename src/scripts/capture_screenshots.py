import asyncio
from playwright.async_api import async_playwright
import os
import time

async def capture_screenshots():
    screenshot_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "demo assets", "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    
    print(f"Saving screenshots to {screenshot_dir}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        print("Navigating to Dashboard...")
        try:
            await page.goto("http://localhost:8000/dashboard/index.html")
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Dashboard unreachable: {e}")
            await browser.close()
            return

        # 1. Dashboard Overview
        await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_01_dashboard_overview.png"))
        
        # 11. System configuration
        config_box = await page.locator('#config-panel').bounding_box()
        if config_box:
            await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_11_system_configuration.png"), clip=config_box)

        # 12. Demo mode toggle
        demo_btn = page.locator('#demo-mode-toggle')
        await demo_btn.hover()
        await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_12_demo_mode_toggle.png"))
        
        print("Triggering Demo Mode...")
        await demo_btn.click()
        
        # 2. Activity Feed overview
        await page.wait_for_timeout(2000)
        feed_box = await page.locator('#activity-feed').bounding_box()
        if feed_box:
            await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_02_activity_feed.png"), clip=feed_box)

        # 3. Issue webhook received
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_03_issue_received.png"))
        
        # 4. AI analysis in progress
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_04_ai_analysis_progress.png"))
        
        # 5. Action executed
        await page.wait_for_timeout(4000)
        await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_05_action_executed.png"))

        # 6. MR webhook received
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_06_mr_received.png"))

        # 7. MR diff analysis
        await page.wait_for_timeout(2000)
        ai_box = await page.locator('#ai-analysis-panel').bounding_box()
        if ai_box:
            await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_07_mr_diff_analysis.png"), clip=ai_box)

        # 8. MR review posted
        await page.wait_for_timeout(3000)
        await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_08_mr_review_posted.png"))

        # 9. Pipeline monitoring
        await page.wait_for_timeout(4000)
        pipe_box = await page.locator('#pipeline-board').bounding_box()
        if pipe_box:
            await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_09_pipeline_monitoring.png"), clip=pipe_box)

        # 10. Entity dashboard
        await page.wait_for_timeout(4000)
        entity_box = await page.locator('#entity-dashboard').bounding_box()
        if entity_box:
            await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_10_entity_dashboard.png"), clip=entity_box)

        # 13. Mock mode indicator
        await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_13_mock_mode_indicator.png"))
        
        # 14. Architecture diagram
        await page.goto("http://localhost:8000/docs") # Fallback since we don't have mermaid natively rendering
        await page.screenshot(path=os.path.join(screenshot_dir, "screenshot_14_architecture_diagram.png"))

        # 15. Terminal logs - can't be captured via playwright purely, will be captured by screenshotting a mock element or terminal tool
        
        print("Screenshots captured successfully.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_screenshots())

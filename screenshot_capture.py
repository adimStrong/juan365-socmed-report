#!/usr/bin/env python3
"""
Dashboard Screenshot Capture using Playwright
Captures full dashboard view from Vercel-hosted analytics sites
"""

import asyncio
import os
import tempfile
from datetime import datetime
from pathlib import Path


async def capture_dashboard_screenshot(
    url: str,
    output_path: str = None,
    viewport_width: int = 1400,
    viewport_height: int = 900,
    full_page: bool = False,
    date_filter: str = "thismonth"
) -> str:
    """
    Capture a single screenshot of the dashboard (legacy function).
    Use capture_dashboard_screenshots() for split screenshots.
    """
    from playwright.async_api import async_playwright

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(tempfile.gettempdir(), f"dashboard_{timestamp}.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height}
        )
        page = await context.new_page()

        full_url = url if url.startswith("http") else f"https://{url}"
        await page.goto(full_url, wait_until="networkidle")
        await asyncio.sleep(4)

        # Click date filter
        filter_buttons = {
            "7days": "Last 7 days", "30days": "Last 30 days",
            "60days": "Last 60 days", "90days": "Last 90 days",
            "thismonth": "This Month", "lastmonth": "Last Month",
            "all": "All Time", "alltime": "All Time"
        }
        btn_text = filter_buttons.get(date_filter.lower(), "This Month")
        try:
            btn = page.locator(f"button:text-is('{btn_text}')")
            if await btn.count() > 0:
                await btn.click()
                await asyncio.sleep(3)
        except:
            pass

        await page.screenshot(path=output_path, full_page=full_page)
        await browser.close()

    return output_path


async def capture_dashboard_screenshots(
    url: str,
    output_dir: str = None,
    date_filter: str = "thismonth"
) -> list:
    """
    Capture TWO screenshots of the dashboard:
    1. Top section: From top until end of "Pages Performance Summary" table
    2. Bottom section: From "Top Performing Posts" until end of "Monthly Performance"

    Args:
        url: Dashboard URL
        output_dir: Directory to save screenshots (default: temp)
        date_filter: Date range filter

    Returns:
        List of paths to saved screenshot files [screenshot1, screenshot2]
    """
    from playwright.async_api import async_playwright

    if output_dir is None:
        output_dir = tempfile.gettempdir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot1_path = os.path.join(output_dir, f"dashboard_top_{timestamp}.png")
    screenshot2_path = os.path.join(output_dir, f"dashboard_bottom_{timestamp}.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900}
        )
        page = await context.new_page()

        # Navigate to dashboard
        full_url = url if url.startswith("http") else f"https://{url}"
        print(f"  Loading {full_url}...")
        await page.goto(full_url, wait_until="networkidle")

        # Wait for charts to render
        print(f"  Waiting for charts to load...")
        await asyncio.sleep(5)

        # Click date filter
        filter_buttons = {
            "7days": "Last 7 days", "30days": "Last 30 days",
            "60days": "Last 60 days", "90days": "Last 90 days",
            "thismonth": "This Month", "lastmonth": "Last Month",
            "all": "All Time", "alltime": "All Time"
        }
        btn_text = filter_buttons.get(date_filter.lower(), "This Month")
        try:
            btn = page.locator(f"button:text-is('{btn_text}')")
            if await btn.count() > 0:
                await btn.click()
                print(f"  Selected: {btn_text}")
                await asyncio.sleep(3)
        except Exception as e:
            print(f"  Warning: Could not click filter: {e}")

        # Scroll to load all content first
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)

        # Use JavaScript to find absolute positions of key elements
        positions = await page.evaluate("""
            () => {
                const result = {
                    pagesTableEnd: null,
                    topPostsStart: null,
                    monthlyPerfEnd: null
                };

                // Find all h2 headings
                const headings = document.querySelectorAll('h2');

                for (const h of headings) {
                    const text = h.textContent.trim();

                    // Find "Pages Performance Summary" - we want to capture until end of its table
                    if (text.includes('Pages Performance Summary')) {
                        // Get the parent card/container that holds the table
                        let container = h.closest('.rounded-lg') || h.parentElement;
                        if (container) {
                            const rect = container.getBoundingClientRect();
                            result.pagesTableEnd = rect.bottom + window.scrollY + 30;
                        }
                    }

                    // Find "Top Performing Posts" - start of second screenshot
                    if (text.includes('Top Performing Posts')) {
                        const rect = h.getBoundingClientRect();
                        result.topPostsStart = rect.top + window.scrollY - 20;
                    }

                    // Find "Monthly Performance" - end of second screenshot
                    if (text.includes('Monthly Performance')) {
                        let container = h.closest('.rounded-lg') || h.parentElement;
                        if (container) {
                            const rect = container.getBoundingClientRect();
                            result.monthlyPerfEnd = rect.bottom + window.scrollY + 30;
                        }
                    }
                }

                return result;
            }
        """)

        print(f"  Element positions: {positions}")

        # SCREENSHOT 1: Top section (from top to Pages Performance Summary)
        print(f"  Capturing screenshot 1 (top section)...")
        try:
            clip_height = positions.get('pagesTableEnd') or 1200
            clip_height = min(clip_height, 2000)  # Cap at 2000px

            await page.screenshot(
                path=screenshot1_path,
                clip={"x": 0, "y": 0, "width": 1400, "height": clip_height},
                full_page=True
            )
            print(f"  Screenshot 1 saved: {screenshot1_path} (height: {clip_height}px)")
        except Exception as e:
            print(f"  Warning: Error capturing top section: {e}")
            await page.screenshot(path=screenshot1_path, full_page=True)

        # SCREENSHOT 2: Bottom section (Top Performing Posts to Monthly Performance)
        print(f"  Capturing screenshot 2 (bottom section)...")
        try:
            start_y = positions.get('topPostsStart') or 1200
            end_y = positions.get('monthlyPerfEnd') or (start_y + 1200)
            clip_height = end_y - start_y
            clip_height = min(clip_height, 1800)  # Cap at 1800px

            await page.screenshot(
                path=screenshot2_path,
                clip={"x": 0, "y": start_y, "width": 1400, "height": clip_height},
                full_page=True
            )
            print(f"  Screenshot 2 saved: {screenshot2_path} (y: {start_y}, height: {clip_height}px)")
        except Exception as e:
            print(f"  Warning: Error capturing bottom section: {e}")
            await page.screenshot(path=screenshot2_path, full_page=True)

        await browser.close()

    return [screenshot1_path, screenshot2_path]


def capture_screenshot_sync(url: str, **kwargs) -> str:
    """Synchronous wrapper for capture_dashboard_screenshot (single screenshot)."""
    return asyncio.run(capture_dashboard_screenshot(url, **kwargs))


def capture_screenshots_sync(url: str, **kwargs) -> list:
    """Synchronous wrapper for capture_dashboard_screenshots (two screenshots)."""
    return asyncio.run(capture_dashboard_screenshots(url, **kwargs))


# Configuration per project
DASHBOARD_CONFIGS = {
    "juanstudio": {
        "url": "juanstudio-analytics.vercel.app",
        "chat_id": "-5157398384",
        "db_path": r"C:\Users\us\Desktop\juanstudio_project\data\juanstudio_analytics.db",
        "project_name": "JuanStudio"
    },
    "juanbabes": {
        "url": "juanbabes-analytics.vercel.app",
        "chat_id": "-5112452649",
        "db_path": r"C:\Users\us\Desktop\juanbabes_project\data\juanbabes_analytics.db",
        "project_name": "JuanBabes"
    },
    "juan365": {
        "url": "juan365-socmed-report.vercel.app",
        "chat_id": "-5118984778",
        "db_path": r"C:\Users\us\Desktop\juan365_socmed_report\data\juan365_socmed.db",
        "project_name": "Juan365"
    }
}


if __name__ == "__main__":
    import sys
    project = sys.argv[1] if len(sys.argv) > 1 else "juanstudio"
    config = DASHBOARD_CONFIGS.get(project)

    if config:
        print(f"Capturing {config['project_name']} dashboard...")
        path = capture_screenshot_sync(config["url"])
        print(f"Done! Screenshot: {path}")
    else:
        print(f"Unknown project: {project}")
        print(f"Available: {list(DASHBOARD_CONFIGS.keys())}")

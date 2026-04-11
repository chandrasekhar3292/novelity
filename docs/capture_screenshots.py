"""Capture screenshots of NoveltyNet pages using Selenium."""
import subprocess
import sys
import os

# Try using playwright for screenshots
def capture_with_playwright():
    from playwright.sync_api import sync_playwright

    out_dir = os.path.join(os.path.dirname(__file__), "screenshots")
    os.makedirs(out_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # 1. Landing page
        page.goto("http://localhost:3000", wait_until="networkidle")
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(out_dir, "01_landing.png"), full_page=False)
        print("Captured: 01_landing.png")

        # 2. Analyze page (empty)
        page.goto("http://localhost:3000/analyze", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(out_dir, "02_analyze_empty.png"), full_page=False)
        print("Captured: 02_analyze_empty.png")

        # 3. Analyze with results
        page.fill('textarea', 'Using graph neural networks to predict protein-ligand binding affinity for drug discovery in rare diseases')
        page.click('button:has-text("Analyze")')
        page.wait_for_timeout(8000)  # Wait for API response
        page.screenshot(path=os.path.join(out_dir, "03_analyze_results.png"), full_page=True)
        print("Captured: 03_analyze_results.png")

        # 4. Corpus page
        page.goto("http://localhost:3000/corpus", wait_until="networkidle")
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(out_dir, "04_corpus.png"), full_page=False)
        print("Captured: 04_corpus.png")

        # 5. Swagger docs
        page.goto("http://localhost:8001/docs", wait_until="networkidle")
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(out_dir, "05_swagger.png"), full_page=False)
        print("Captured: 05_swagger.png")

        browser.close()
    print(f"\nAll screenshots saved to: {out_dir}")

if __name__ == "__main__":
    try:
        capture_with_playwright()
    except Exception as e:
        print(f"Error: {e}")
        print("Installing playwright...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        capture_with_playwright()

from playwright.sync_api import sync_playwright

def test_browser():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, chromium_sandbox=False)
            page = browser.new_page()
            page.goto('https://www.youtube.com/watch?v=8jPQjjsBbIc')
            print(page.title())
            browser.close()
            print("Browser test successful!")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_browser()
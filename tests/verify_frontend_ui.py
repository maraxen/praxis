import sys

from playwright.sync_api import sync_playwright


def verify():
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate to playground
        print("Navigating to http://localhost:4200/app/playground...")
        page.goto("http://localhost:4200/app/playground", wait_until="networkidle")

        # Open inventory dialog
        print("Opening inventory dialog...")
        # The button has matTooltip="Open Inventory Dialog" and aria-label="Open Inventory Dialog"
        page.click('button[aria-label="Open Inventory Dialog"]')

        # Wait for dialog to appear
        print("Waiting for dialog...")
        page.wait_for_selector('h2:has-text("Playground Inventory")')
        print("Inventory dialog opened.")

        # Click "Browse & Add" tab
        print("Clicking 'Browse & Add' tab...")
        # The tab text is "Browse & Add"
        page.click('.mdc-tab:has-text("Browse & Add")')

        # In Stepper: Select "Machine" card
        print("Selecting 'Machine' type...")
        page.click('.type-card:has-text("Machine")')

        # Click Continue
        print("Clicking Continue...")
        page.click('button:has-text("Continue")')

        # Verify categories are present
        print("Waiting for categories...")
        page.wait_for_selector("mat-chip-listbox")
        categories = page.locator("mat-chip-option").all_inner_texts()
        print(f"Machine categories found: {categories}")
        if not categories:
            print("ERROR: No machine categories found!")
            browser.close()
            sys.exit(1)

        # Click Back
        print("Clicking Back...")
        page.click('button:has-text("Back")')

        # Select "Resource" card
        print("Selecting 'Resource' type...")
        page.click('.type-card:has-text("Resource")')

        # Click Continue
        print("Clicking Continue...")
        page.click('button:has-text("Continue")')

        # Verify categories are present for resources
        print("Waiting for resource categories...")
        page.wait_for_selector("mat-chip-listbox")
        res_categories = page.locator("mat-chip-option").all_inner_texts()
        print(f"Resource categories found: {res_categories}")
        if not res_categories:
            print("ERROR: No resource categories found!")
            browser.close()
            sys.exit(1)

        print("Frontend UI verification successful!")
        browser.close()

if __name__ == "__main__":
    verify()

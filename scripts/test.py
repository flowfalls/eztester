import os
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Credentials


class SimpleGOVUKAutomator:
    """Simplified GOV.UK automation with better compatibility"""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.email = GOVUK_EMAIL
        self.password = GOVUK_PASSWORD

        logger.info(f"Initializing automation (headless={headless})")
        logger.info(f"Email: {self.email}")
        logger.info(f"Password: {'*' * len(self.password)}")

    async def run_automation(self) -> Dict[str, Any]:
        """Main automation function with step-by-step approach"""

        # Simple browser config - only use supported parameters
        browser_config = BrowserConfig(
            headless=self.headless,
            verbose=True
        )

        result_log = {
            "success": False,
            "steps": [],
            "errors": [],
            "final_url": None,
            "timestamp": datetime.now().isoformat()
        }

        logger.info("🚀 Starting GOV.UK sign-in automation...")

        async with AsyncWebCrawler(config=browser_config) as crawler:

            try:
                # Step 1: Load initial page
                logger.info("📍 Step 1: Loading GOV.UK sign-in page...")

                initial_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    wait_for_images=False,
                    delay_before_return_html=3.0
                )

                initial_url = "https://signin.account.gov.uk/sign-in-or-create"
                initial_result = await crawler.arun(url=initial_url, config=initial_config)

                if not initial_result.success:
                    error_msg = f"Failed to load initial page: {initial_result.error_message}"
                    logger.error(f"❌ {error_msg}")
                    result_log["errors"].append(error_msg)
                    return result_log

                logger.info(f"✅ Initial page loaded: {initial_result.url}")
                result_log["steps"].append({"step": 1, "success": True, "url": initial_result.url})

                # Step 2: Click sign in and navigate to email page
                logger.info("🔘 Step 2: Navigating to email entry...")

                # JavaScript to find and click sign in, then navigate to email page
                signin_and_email_js = f"""
                // Step 2a: Look for sign in button or direct navigation
                let signInButton = null;

                // Try to find sign in button
                const signInSelectors = [
                    'a[href*="enter-email"]',
                    'a:contains("Sign in")',
                    '.govuk-button:contains("Sign in")',
                    'button:contains("Sign in")'
                ];

                // Simple text search for sign in
                const allLinks = document.querySelectorAll('a, button');
                for (const element of allLinks) {{
                    const text = element.textContent.toLowerCase().trim();
                    if (text.includes('sign in') || text.includes('start now')) {{
                        signInButton = element;
                        break;
                    }}
                }}

                if (signInButton) {{
                    console.log('Clicking sign in button:', signInButton.textContent);
                    signInButton.click();

                    // Wait for navigation
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }}

                // Step 2b: Now we should be on email page, enter email
                const emailSelectors = ['#email', 'input[name="email"]', 'input[type="email"]'];
                let emailInput = null;

                for (const selector of emailSelectors) {{
                    emailInput = document.querySelector(selector);
                    if (emailInput) break;
                }}

                if (emailInput) {{
                    console.log('Found email input, entering email...');
                    emailInput.focus();
                    emailInput.value = '{self.email}';
                    emailInput.dispatchEvent(new Event('input', {{bubbles: true}}));
                    emailInput.dispatchEvent(new Event('change', {{bubbles: true}}));

                    // Find continue button
                    const continueButtons = document.querySelectorAll('button, input[type="submit"], .govuk-button');
                    for (const btn of continueButtons) {{
                        const text = (btn.textContent || btn.value || '').toLowerCase();
                        if (text.includes('continue') || text.includes('next') || btn.type === 'submit') {{
                            console.log('Clicking continue button after email');
                            btn.click();
                            break;
                        }}
                    }}

                    // Wait for navigation to password page
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }} else {{
                    console.error('Email input not found');
                }}

                // Return current state
                return {{
                    currentUrl: window.location.href,
                    pageTitle: document.title,
                    hasEmailInput: !!emailInput,
                    emailEntered: !!emailInput
                }};
                """

                email_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    js_code=signin_and_email_js,
                    delay_before_return_html=5.0
                )

                initial_url = "https://signin.account.gov.uk/sign-in-or-create"
                initial_result = await crawler.arun(url=initial_url, config=initial_config)


                result_log["steps"].append({"step": 2, "success": email_result.success, "action": "email_entry"})
                logger.info("✅ Email entry step completed")

                # Step 3: Enter password and submit
                logger.info("🔒 Step 3: Entering password and submitting...")

                password_js = f"""
                // Look for password input
                const passwordSelectors = ['#password', 'input[name="password"]', 'input[type="password"]'];
                let passwordInput = null;

                for (const selector of passwordSelectors) {{
                    passwordInput = document.querySelector(selector);
                    if (passwordInput) break;
                }}

                if (passwordInput) {{
                    console.log('Found password input, entering password...');
                    passwordInput.focus();
                    passwordInput.value = '{self.password}';
                    passwordInput.dispatchEvent(new Event('input', {{bubbles: true}}));
                    passwordInput.dispatchEvent(new Event('change', {{bubbles: true}}));

                    // Find and click submit button
                    const submitButtons = document.querySelectorAll('button, input[type="submit"], .govuk-button');
                    for (const btn of submitButtons) {{
                        const text = (btn.textContent || btn.value || '').toLowerCase();
                        if (text.includes('sign in') || text.includes('continue') || text.includes('submit') || btn.type === 'submit') {{
                            console.log('Clicking submit button after password');
                            btn.click();
                            break;
                        }}
                    }}

                    // Wait for final navigation
                    await new Promise(resolve => setTimeout(resolve, 5000));
                }} else {{
                    console.error('Password input not found');
                }}

                // Check for any error messages
                const errorElements = document.querySelectorAll('.govuk-error-message, .error-message, [role="alert"]');
                const errors = Array.from(errorElements).map(el => el.textContent.trim()).filter(text => text);

                return {{
                    currentUrl: window.location.href,
                    pageTitle: document.title,
                    hasPasswordInput: !!passwordInput,
                    passwordEntered: !!passwordInput,
                    errors: errors,
                    isLoginPage: window.location.href.includes('sign-in') || window.location.href.includes('login'),
                    isSuccessPage: !window.location.href.includes('sign-in') && !window.location.href.includes('login')
                }};
                """

                password_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    js_code=password_js,
                    delay_before_return_html=7.0
                )

                password_result = await crawler.arun(config=password_config)

                result_log["steps"].append({"step": 3, "success": password_result.success, "action": "password_entry"})

                # Step 4: Final check
                logger.info("🏁 Step 4: Checking final result...")

                final_check_js = """
                // Final status check
                const currentUrl = window.location.href;
                const pageTitle = document.title;

                // Look for error messages
                const errorSelectors = ['.govuk-error-message', '.error-message', '[role="alert"]', '.govuk-error-summary'];
                const errors = [];

                for (const selector of errorSelectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const el of elements) {
                        if (el.textContent.trim()) {
                            errors.push(el.textContent.trim());
                        }
                    }
                }

                // Determine if we're successful
                const isLoginPage = currentUrl.includes('sign-in') || currentUrl.includes('login') || currentUrl.includes('enter-');
                const hasErrors = errors.length > 0;
                const isSuccessPage = !isLoginPage && !hasErrors;

                return {
                    currentUrl: currentUrl,
                    pageTitle: pageTitle,
                    errors: errors,
                    isLoginPage: isLoginPage,
                    isSuccessPage: isSuccessPage,
                    hasErrors: hasErrors
                };
                """

                final_config = CrawlerRunConfig(
                    cache_mode=CacheMode.BYPASS,
                    js_code=final_check_js,
                    delay_before_return_html=2.0
                )

                final_result = await crawler.arun(config=final_config)

                # Determine final success
                final_url = "unknown"
                try:
                    # Try to get the current URL from the page
                    current_url_js = "window.location.href"
                    url_config = CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        js_code=current_url_js
                    )
                    url_result = await crawler.arun(config=url_config)
                    # Extract URL from result if possible
                    final_url = getattr(url_result, 'url', 'unknown')
                except:
                    pass

                result_log["final_url"] = final_url

                # Simple success determination based on URL
                if "sign-in" not in final_url.lower() and "login" not in final_url.lower() and "enter-" not in final_url.lower():
                    result_log["success"] = True
                    logger.info(f"✅ Sign-in appears successful! Final URL: {final_url}")
                else:
                    result_log["success"] = False
                    result_log["errors"].append(f"Still on login page: {final_url}")
                    logger.warning(f"⚠️ Still on login page: {final_url}")

                result_log["steps"].append({"step": 4, "success": True, "action": "final_check", "url": final_url})

            except Exception as e:
                error_msg = f"Automation failed: {str(e)}"
                logger.error(f"❌ {error_msg}")
                result_log["errors"].append(error_msg)

        return result_log

def get_twilio_messages(from_pattern: str = "GOV", hours_back: int = 24) -> List[Dict]:
    """Get messages from Twilio with pattern matching"""

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.error("❌ Twilio credentials not configured")
        return []

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Get recent messages
        date_after = datetime.now() - timedelta(hours=hours_back)

        # Get all recent messages and filter by pattern
        all_messages = client.messages.list(
            limit=100,
            date_sent_after=date_after
        )

        # Filter messages that match the pattern
        matching_messages = []
        for msg in all_messages:
            if from_pattern.upper() in (msg.from_ or "").upper():
                matching_messages.append({
                    'from': msg.from_,
                    'to': msg.to,
                    'body': msg.body,
                    'date_sent': msg.date_sent,
                    'status': msg.status
                })

        logger.info(f"📱 Found {len(matching_messages)} messages matching '{from_pattern}'")
        return matching_messages

    except Exception as e:
        logger.error(f"❌ Error getting Twilio messages: {e}")
        return []

async def main():
    """Main function with command line arguments"""

    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python script.py automate        # Run GOV.UK automation")
        print("  python script.py messages        # Check for verification messages")
        print("  python script.py automate-visible # Run with visible browser")
        return

    command = sys.argv[1].lower()

    if command in ["automate", "automate-visible"]:
        # Run automation
        headless = command == "automate"

        automator = SimpleGOVUKAutomator(headless=headless)
        result = await automator.run_automation()

        # Print results
        print("\n" + "="*60)
        print("📊 AUTOMATION RESULTS")
        print("="*60)
        print(f"Success: {'✅ YES' if result['success'] else '❌ NO'}")
        print(f"Final URL: {result.get('final_url', 'Unknown')}")
        print(f"Steps completed: {len(result['steps'])}")

        if result['errors']:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  ❌ {error}")

        print("\nStep details:")
        for step in result['steps']:
            status = "✅" if step['success'] else "❌"
            print(f"  {status} Step {step['step']}: {step.get('action', 'N/A')}")

        # Save results
        result_file = Path(f"automation_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n📄 Results saved to: {result_file}")

    elif command == "messages":
        # Check for verification messages
        print("🔍 Searching for GOV.UK verification messages...")

        messages = get_twilio_messages("GOV", hours_back=48)

        if messages:
            print(f"\n📱 Found {len(messages)} messages:")
            print("="*60)
            for msg in messages:
                print(f"From: {msg['from']}")
                print(f"Date: {msg['date_sent']}")
                print(f"Body: {msg['body']}")
                print("-" * 40)
        else:
            print("📭 No matching messages found")

    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    # Set environment variables for security:
    # export GOVUK_EMAIL="your.email@example.com"
    # export GOVUK_PASSWORD="your_password"
    # export TWILIO_ACCOUNT_SID="your_account_sid"
    # export TWILIO_AUTH_TOKEN="your_auth_token"

    asyncio.run(main())
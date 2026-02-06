"""ESS (Employee Self-Service) Attendance Watcher

Monitors attendance status and creates approval workflows for marking attendance.
Uses Playwright for browser automation to interact with ESS system.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Browser, sync_playwright

from ai_employee import config
from ai_employee.utils import ensure_dir, load_json, log_line, save_json, utc_now_iso, write_text
from ai_employee.watchers.base import BaseWatcher


class ESSWatcher(BaseWatcher):
    """Monitor ESS attendance and create marking workflows."""

    def __init__(
        self,
        ess_url: str,
        user_id: str,
        password: str,
        vault_path: Path,
        state_path: Path,
        headless: bool = True,
        check_interval: int = 60,
    ) -> None:
        super().__init__(check_interval=check_interval)
        self.ess_url = ess_url
        self.user_id = user_id
        self.password = password
        self.vault_path = vault_path
        self.state_path = state_path
        self.headless = headless
        self.log_path = config.LOG_DIR / "ess_watcher.log"

    def check(self) -> int:
        """Check ESS attendance status and create approval workflow."""
        try:
            ensure_dir(self.vault_path / "Needs_Action")
            state = load_json(self.state_path, default={"last_checked": None, "marked_dates": []})

            # Check if attendance needs to be marked today
            today = datetime.now().strftime("%Y-%m-%d")
            if today in state.get("marked_dates", []):
                self.log("Attendance already marked for today")
                return 0

            # Use Playwright to check ESS status
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                count = self._check_and_create_workflow(browser, today, state)
                browser.close()

            return count

        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            return 0

    def _check_and_create_workflow(self, browser: Browser, today: str, state: dict) -> int:
        """Check ESS system and create attendance marking workflow."""
        page = browser.new_page()

        try:
            # Navigate to ESS
            self.log(f"Navigating to {self.ess_url}")
            page.goto(self.ess_url, wait_until="domcontentloaded")

            # Login
            self._login(page)

            # Check current attendance status
            attendance_status = self._get_attendance_status(page)
            self.log(f"Current attendance status: {attendance_status}")

            # If not marked, create approval workflow
            if not attendance_status or attendance_status.lower() != "present":
                task_path = self._create_approval_task(today, attendance_status)
                self.log(f"Created attendance approval task: {task_path.name}")
                return 1

            # If already marked, update state
            state["marked_dates"].append(today)
            state["last_checked"] = utc_now_iso()
            save_json(self.state_path, state)
            self.log(f"Attendance already marked for {today}")
            return 0

        finally:
            page.close()

    def _login(self, page) -> None:
        """Login to ESS system."""
        try:
            # Wait for login form and fill credentials
            page.wait_for_selector("input[name='username'], input[name='userID'], input[id*='user']", timeout=10000)

            # Try common username field selectors
            username_selectors = [
                "input[name='username']",
                "input[name='userID']",
                "input[id*='user']",
                "input[placeholder*='ID']",
                "input[placeholder*='User']",
            ]

            username_field = None
            for selector in username_selectors:
                try:
                    username_field = page.query_selector(selector)
                    if username_field:
                        break
                except:
                    pass

            if not username_field:
                raise Exception("Could not find username input field")

            username_field.fill(self.user_id)
            self.log("Username entered")

            # Find and fill password field
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "input[id*='pass']",
                "input[placeholder*='Pass']",
            ]

            password_field = None
            for selector in password_selectors:
                try:
                    password_field = page.query_selector(selector)
                    if password_field:
                        break
                except:
                    pass

            if not password_field:
                raise Exception("Could not find password input field")

            password_field.fill(self.password)
            self.log("Password entered")

            # Click login button
            login_selectors = [
                "button[type='submit']",
                "button:has-text('Login')",
                "button:has-text('Sign In')",
                "button:has-text('Submit')",
            ]

            login_button = None
            for selector in login_selectors:
                try:
                    login_button = page.query_selector(selector)
                    if login_button:
                        break
                except:
                    pass

            if login_button:
                login_button.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                self.log("Login submitted and page loaded")
            else:
                self.log("WARNING: Could not find login button, assuming form auto-submits")
                page.wait_for_load_state("networkidle", timeout=15000)

        except Exception as e:
            self.log(f"LOGIN ERROR: {str(e)}")
            raise

    def _get_attendance_status(self, page) -> str | None:
        """Extract current attendance status from page."""
        try:
            # Look for attendance status indicators
            status_indicators = [
                "text='Present'",
                "text='Absent'",
                "text='On Leave'",
                ":has-text('Status')",
                ".status",
                "#attendance-status",
                "[class*='attendance']",
            ]

            for indicator in status_indicators:
                try:
                    element = page.query_selector(indicator)
                    if element:
                        text = element.inner_text()
                        if text and len(text) > 0:
                            return text.strip()
                except:
                    pass

            self.log("Could not find attendance status on page")
            return None

        except Exception as e:
            self.log(f"ERROR getting attendance status: {str(e)}")
            return None

    def _create_approval_task(self, today: str, current_status: str | None) -> Path:
        """Create an approval workflow task for marking attendance."""
        ensure_dir(self.vault_path / "Needs_Action")
        stamp = utc_now_iso()
        task_name = f"ATTENDANCE_MARK_{today.replace('-', '')}_{stamp.replace(':', '').replace('.', '')}.md"
        task_path = self.vault_path / "Needs_Action" / task_name

        status_text = current_status if current_status else "Unknown"

        content = "\n".join(
            [
                "---",
                "type: attendance_marking",
                "source: ess_watcher",
                "priority: high",
                "status: pending_approval",
                f"created_at: {stamp}",
                f"date: {today}",
                f"current_status: {status_text}",
                "action: mark_present",
                "---",
                "",
                "# ESS Attendance Marking",
                f"## Mark Attendance for {today}",
                f"Current status: **{status_text}**",
                "",
                "### Action Required",
                "Move this file to `/Approved` folder to automatically mark attendance as **Present** in ESS.",
                "",
                "### Details",
                f"- Date: {today}",
                f"- Current Status: {status_text}",
                f"- Action: Mark as Present",
                f"- System: ESS (https://ess.dimionline.com/)",
                "",
                "### Steps (for manual marking if approval fails)",
                "1. Go to https://ess.dimionline.com/",
                "2. Login with your credentials",
                "3. Navigate to Attendance",
                "4. Click Mark Present for today's date",
                "5. Confirm the marking",
                "",
            ]
        )

        write_text(task_path, content)
        return task_path

    def log(self, message: str) -> None:
        """Log a message."""
        log_line(self.log_path, message)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ESS Attendance Watcher")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    parser.add_argument("--interval", type=int, help="Polling interval (seconds)")
    parser.add_argument("--ess-url", type=str, help="ESS system URL")
    parser.add_argument("--user-id", type=str, help="ESS user ID")
    parser.add_argument("--password", type=str, help="ESS password")
    parser.add_argument("--headless", type=bool, default=True, help="Run browser in headless mode")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    # Get configuration from environment or arguments
    ess_url = args.ess_url or os.getenv("ESS_URL", "https://ess.dimionline.com/")
    user_id = args.user_id or os.getenv("ESS_USER_ID")
    password = args.password or os.getenv("ESS_PASSWORD")
    headless = args.headless or os.getenv("ESS_HEADLESS", "true").lower() == "true"
    check_interval = args.interval or int(os.getenv("ESS_CHECK_INTERVAL", "60"))

    if not user_id or not password:
        raise ValueError("ESS_USER_ID and ESS_PASSWORD must be set via environment or arguments")

    watcher = ESSWatcher(
        ess_url=ess_url,
        user_id=user_id,
        password=password,
        vault_path=config.VAULT_PATH,
        state_path=config.STATE_DIR / "ess_watcher.json",
        headless=headless,
        check_interval=check_interval,
    )

    if args.once:
        watcher.check()
    else:
        watcher.run()


if __name__ == "__main__":
    main()

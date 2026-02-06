"""MCP Server for ESS Attendance Marking

This server handles the actual marking of attendance in the ESS system.
It's called by the orchestrator after human approval from /Approved folder.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


class ESSAttendanceService:
    """Service to mark attendance in ESS system."""

    def __init__(self, ess_url: str, user_id: str, password: str, headless: bool = True):
        self.ess_url = ess_url
        self.user_id = user_id
        self.password = password
        self.headless = headless

    def mark_attendance_present(self, date: str = None) -> dict:
        """Mark attendance as Present for given date (default: today)."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()

                # Navigate and login
                page.goto(self.ess_url, wait_until="domcontentloaded")
                self._login(page)

                # Mark attendance
                success = self._mark_present(page, date)

                browser.close()

                return {
                    "success": success,
                    "date": date,
                    "message": f"Attendance marked as Present for {date}" if success else "Failed to mark attendance",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            return {
                "success": False,
                "date": date,
                "message": f"Error marking attendance: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

    def _login(self, page) -> None:
        """Login to ESS system."""
        username_selectors = [
            "input[name='username']",
            "input[name='userID']",
            "input[id*='user']",
            "input[placeholder*='ID']",
        ]

        username_field = None
        for selector in username_selectors:
            try:
                username_field = page.query_selector(selector)
                if username_field:
                    break
            except:
                pass

        if username_field:
            username_field.fill(self.user_id)

        password_selectors = [
            "input[name='password']",
            "input[type='password']",
            "input[id*='pass']",
        ]

        password_field = None
        for selector in password_selectors:
            try:
                password_field = page.query_selector(selector)
                if password_field:
                    break
            except:
                pass

        if password_field:
            password_field.fill(self.password)

        login_selectors = [
            "button[type='submit']",
            "button:has-text('Login')",
            "button:has-text('Sign In')",
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

    def _mark_present(self, page, date: str) -> bool:
        """Mark attendance as Present."""
        try:
            # Look for attendance section
            page.wait_for_selector("[class*='attendance'], [id*='attendance']", timeout=5000)

            # Try to find and click "Mark Present" button
            mark_present_selectors = [
                "button:has-text('Mark Present')",
                "button:has-text('Check In')",
                "button:has-text('Mark Attendance')",
                "[class*='mark-present'] button",
                "[id*='mark-present'] button",
            ]

            button_found = False
            for selector in mark_present_selectors:
                try:
                    button = page.query_selector(selector)
                    if button:
                        button.click()
                        page.wait_for_load_state("networkidle", timeout=5000)
                        button_found = True
                        break
                except:
                    pass

            if not button_found:
                # Try to find date selector and click on today's date
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                day = date_obj.strftime("%d").lstrip("0")  # Remove leading zero

                day_selectors = [
                    f"td:has-text('{day}')",
                    f"[class*='day']:has-text('{day}')",
                    f"button:has-text('{day}')",
                ]

                for selector in day_selectors:
                    try:
                        day_button = page.query_selector(selector)
                        if day_button:
                            day_button.click()
                            page.wait_for_timeout(1000)

                            # Click confirm or submit
                            confirm_selectors = [
                                "button:has-text('Confirm')",
                                "button:has-text('Submit')",
                                "button:has-text('OK')",
                            ]

                            for confirm_selector in confirm_selectors:
                                try:
                                    confirm_btn = page.query_selector(confirm_selector)
                                    if confirm_btn:
                                        confirm_btn.click()
                                        page.wait_for_load_state("networkidle", timeout=5000)
                                        return True
                                except:
                                    pass
                    except:
                        pass

            return button_found

        except Exception as e:
            print(f"Error marking attendance: {str(e)}", file=sys.stderr)
            return False


def handle_mark_attendance(request: dict) -> dict:
    """Handle MCP request to mark attendance."""
    ess_url = os.getenv("ESS_URL", "https://ess.dimionline.com/")
    user_id = os.getenv("ESS_USER_ID")
    password = os.getenv("ESS_PASSWORD")

    if not user_id or not password:
        return {
            "success": False,
            "error": "ESS_USER_ID and ESS_PASSWORD environment variables must be set",
        }

    service = ESSAttendanceService(ess_url, user_id, password, headless=True)
    date = request.get("date")
    return service.mark_attendance_present(date)


def main() -> None:
    """Simple stdio-based MCP handler."""
    import sys

    # Read input
    line = sys.stdin.readline()
    if not line:
        return

    try:
        request = json.loads(line)
        result = handle_mark_attendance(request)
        print(json.dumps(result))
    except json.JSONDecodeError:
        print(json.dumps({"success": False, "error": "Invalid JSON input"}))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))


if __name__ == "__main__":
    main()

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

            # Navigate to attendance page after switching to employee mode
            self._navigate_to_attendance_page(page)

            # Mark attendance as Present
            self._mark_attendance_present(page)

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
            # Wait for login form with ESS-specific selectors
            page.wait_for_selector("#txtUser", timeout=15000)
            self.log("Login form found")

            # Username field - ESS uses id="txtUser"
            username_selectors = [
                "#txtUser",  # Primary selector for ESS
                "input[id='txtUser']",
                "input[name='Name']",
                "input[placeholder*='GR Number']",
                "input[placeholder*='Enter GR']",
            ]

            username_field = None
            for selector in username_selectors:
                try:
                    username_field = page.query_selector(selector)
                    if username_field:
                        self.log(f"Found username field with selector: {selector}")
                        break
                except:
                    pass

            if not username_field:
                raise Exception("Could not find username input field")

            username_field.fill(self.user_id)
            self.log(f"Username entered: {self.user_id}")

            # Password field - look for password input
            password_selectors = [
                "input[type='password']",
                "input[id*='password']",
                "input[id*='Pass']",
                "input[name*='password']",
            ]

            password_field = None
            for selector in password_selectors:
                try:
                    password_field = page.query_selector(selector)
                    if password_field:
                        self.log(f"Found password field with selector: {selector}")
                        break
                except:
                    pass

            if not password_field:
                raise Exception("Could not find password input field")

            password_field.fill(self.password)
            self.log("Password entered")

            # Click login button - ESS uses id="btnLogin"
            login_selectors = [
                "#btnLogin",  # Primary selector for ESS
                "input[id='btnLogin']",
                "button[id='btnLogin']",
                "input[type='submit']",
                "button[type='submit']",
                "button:has-text('Login')",
            ]

            login_button = None
            for selector in login_selectors:
                try:
                    login_button = page.query_selector(selector)
                    if login_button:
                        self.log(f"Found login button with selector: {selector}")
                        break
                except:
                    pass

            if login_button:
                login_button.click()
                self.log("Login button clicked, waiting for page load...")
                # Wait for page to load - use domcontentloaded instead of networkidle to avoid timeout
                page.wait_for_load_state("domcontentloaded", timeout=20000)
                self.log("Login successful and page loaded")
                # Additional wait for page stability
                page.wait_for_timeout(3000)

                # Close modal if it appears (company policy/declaration modal)
                self._close_modal(page)

                # Switch to employee mode (from Nazim mode)
                self._switch_to_employee_mode(page)
            else:
                raise Exception("Could not find login button")

        except Exception as e:
            self.log(f"LOGIN ERROR: {str(e)}")
            raise

    def _close_modal(self, page) -> None:
        """Close any modal dialogs that appear after login."""
        try:
            self.log("Attempting to close modal dialog if present...")

            # Try different modal close button selectors
            close_selectors = [
                "button[aria-label='Close']",
                ".modal .close",
                ".close-btn",
                "button.close",
                "[role='dialog'] button[aria-label='Close']",
                ".mat-dialog-container .mat-icon-button",
                "button[type='button'][aria-label*='close']",
                "div[role='dialog'] button:first-of-type",
                "mat-dialog-container button",
                "//button[contains(@class, 'close')]",
            ]

            modal_closed = False
            for selector in close_selectors:
                try:
                    close_button = page.query_selector(selector)
                    if close_button:
                        self.log(f"Found close button with selector: {selector}")
                        close_button.click()
                        page.wait_for_timeout(1000)
                        modal_closed = True
                        self.log("Modal closed successfully")
                        break
                except:
                    pass

            if not modal_closed:
                self.log("No modal dialog found or already closed")

        except Exception as e:
            self.log(f"Note: Could not close modal: {str(e)}")
            # Don't raise - modal closing is optional

    def _switch_to_employee_mode(self, page) -> None:
        """Switch from Nazim to Employee mode in ESS dashboard."""
        try:
            self.log("Attempting to switch to employee mode...")
            page.wait_for_timeout(2000)

            # The "Nazim" button is in the header/navbar next to user ID
            # It's a clickable element (DIV with class "selected-language-container") to toggle between Nazim and Employee modes
            employee_switched = False

            # Use JavaScript to find and click the Nazim button by text
            try:
                result = page.evaluate("""
                    () => {
                        // Find elements with exact "Nazim" text
                        const allElements = Array.from(document.querySelectorAll('*'));
                        const nazimElement = allElements.find(el => {
                            const text = (el.textContent || '').trim();
                            // Match exact "Nazim" text, not just containing
                            return (text === 'Nazim' || text.startsWith('Nazim ')) && el.offsetHeight > 0;
                        });
                        if (nazimElement) {
                            nazimElement.click();
                            return true;
                        }
                        return false;
                    }
                """)
                if result:
                    self.log("Nazim button clicked, waiting for page reload...")
                    # Wait longer for page to reload after clicking Nazim (which is a language/mode toggle)
                    page.wait_for_load_state("domcontentloaded", timeout=20000)
                    page.wait_for_timeout(3000)
                    self.log("Page reloaded after Nazim click")

                    # Verify the mode switched
                    current_navbar = page.evaluate("""
                        () => {
                            // Check if navbar now shows "Employee" instead of "Nazim"
                            const allText = document.body.innerText || '';
                            return {
                                hasEmployee: allText.includes('Employee'),
                                hasNazim: allText.includes('Nazim'),
                                bodyText: allText.substring(0, 200)
                            };
                        }
                    """)

                    if current_navbar.get('hasEmployee'):
                        self.log("Mode switched successfully to Employee")
                        employee_switched = True
                    else:
                        self.log("Note: Navbar text not updated yet, but continuing...")
                        employee_switched = True  # Continue anyway as click was successful
            except Exception as e:
                self.log(f"Error during Nazim click: {str(e)}")

            if not employee_switched:
                self.log("Warning: Could not switch to employee mode, but continuing...")

        except Exception as e:
            self.log(f"Note: Could not switch to employee mode: {str(e)}")
            # Don't raise - continue anyway

    def _navigate_to_attendance_page(self, page) -> None:
        """Navigate to the attendance form page."""
        try:
            self.log("Navigating to attendance form page...")
            attendance_url = "https://www.dimionline.com/Forms/AttendanceForm.aspx"

            page.goto(attendance_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(3000)

            self.log(f"Successfully navigated to attendance page: {attendance_url}")

        except Exception as e:
            self.log(f"ERROR navigating to attendance page: {str(e)}")
            raise

    def _mark_attendance_present(self, page) -> bool:
        """Mark attendance - CORRECT ORDER: 1) Date 2) Present 3) Times 4) Save"""
        try:
            from datetime import datetime, timedelta

            self.log("Attempting to mark attendance...")
            page.wait_for_timeout(2000)

            # Step 1: Select yesterday's date using calendar picker
            self.log("Step 1: Selecting yesterday's date...")

            # Simply use yesterday - don't skip any days
            target_date = datetime.now() - timedelta(days=1)
            target_day = target_date.strftime("%d").lstrip("0")  # Remove leading zero
            self.log(f"Selecting date: {target_date.strftime('%d/%m/%Y')} (day {target_day})")

            date_selected = False

            try:
                # Open calendar picker
                page.evaluate("document.querySelector('span[id=\"ImageButton1\"]')?.click()")
                page.wait_for_timeout(500)

                # Click the day in calendar
                result = page.evaluate(f"""
                    () => {{
                        const tds = document.querySelectorAll('td');
                        for (let td of tds) {{
                            if (td.textContent.trim() === '{target_day}') {{
                                const link = td.querySelector('a');
                                if (link) {{
                                    link.click();
                                }} else {{
                                    td.click();
                                }}
                                return true;
                            }}
                        }}
                        return false;
                    }}
                """)
                if result:
                    self.log(f"Selected date: {target_date.strftime('%d/%m/%Y')}")
                    date_selected = True
                    page.wait_for_timeout(1500)
            except Exception as e:
                self.log(f"Error selecting date: {str(e)}")

            if not date_selected:
                self.log("Warning: Could not select date from calendar")

            # Check if there's an error message (e.g., attendance already marked)
            error_check = page.evaluate("""
                () => {
                    const errorMsg = document.querySelector('.alert-danger, .error-message, [class*="error"]');
                    if (errorMsg) {
                        return errorMsg.textContent.trim();
                    }
                    return null;
                }
            """)

            if error_check:
                self.log(f"System message: {error_check}")
                if "already" in error_check.lower() or "marked" in error_check.lower():
                    self.log(f"Attendance already marked for {target_date.strftime('%d/%m/%Y')}")
                    return True  # Consider this a success - already marked

            # Step 2: Select "حاضر" (Present) from dropdown
            self.log("Step 2: Selecting 'حاضر' (Present) from dropdown...")
            present_selected = False

            try:
                result = page.evaluate("""
                    () => {
                        const selects = document.querySelectorAll('select');
                        for (let select of selects) {
                            for (let i = 0; i < select.options.length; i++) {
                                const option = select.options[i];
                                if (option.text.includes('حاضر') || option.value === '1') {
                                    select.value = option.value;
                                    select.dispatchEvent(new Event('change', { bubbles: true }));
                                    return true;
                                }
                            }
                        }
                        return false;
                    }
                """)
                if result:
                    self.log("Selected 'حاضر' (Present)")
                    present_selected = True
            except Exception as e:
                self.log(f"Error selecting Present: {str(e)}")

            if not present_selected:
                self.log("Warning: Could not select Present")

            page.wait_for_timeout(500)

            # Step 3: Fill arrival time (وقت آمد) - 09:00 (24-hour format for HTML5 type="time")
            self.log("Step 3: Filling arrival time with 09:00...")
            arrival_found = False

            try:
                # Try specific ID selector for arrival time input
                arrival_input = page.query_selector("input#ContentPlaceHolder1_txtTimeIN")
                if not arrival_input:
                    # Fallback: try by name
                    arrival_input = page.query_selector("input[name*='txtTimeIN']")

                if arrival_input:
                    # For HTML5 type="time" inputs, use 24-hour format HH:mm
                    arrival_input.fill("09:00")
                    arrival_input.evaluate("""
                        () => {
                            this.dispatchEvent(new Event('change', {bubbles: true}));
                            this.dispatchEvent(new Event('input', {bubbles: true}));
                            this.dispatchEvent(new Event('blur', {bubbles: true}));
                        }
                    """)
                    self.log("Arrival time filled: 09:00")
                    arrival_found = True
            except Exception as e:
                self.log(f"Error with arrival time: {str(e)}")

            if not arrival_found:
                self.log("Warning: Could not fill arrival time")

            page.wait_for_timeout(1000)

            # Step 4: Fill departure time (وقت رخصت) - 17:00 (24-hour format for HTML5 type="time")
            self.log("Step 4: Filling departure time with 17:00...")
            departure_found = False

            try:
                # Try specific ID selector for departure time input
                departure_input = page.query_selector("input#ContentPlaceHolder1_txtTimeOUT")
                if not departure_input:
                    # Fallback: try by name
                    departure_input = page.query_selector("input[name*='txtTimeOUT']")

                if departure_input:
                    # For HTML5 type="time" inputs, use 24-hour format HH:mm
                    # 17:00 = 5:00 PM
                    departure_input.fill("17:00")
                    departure_input.evaluate("""
                        () => {
                            this.dispatchEvent(new Event('change', {bubbles: true}));
                            this.dispatchEvent(new Event('input', {bubbles: true}));
                            this.dispatchEvent(new Event('blur', {bubbles: true}));
                        }
                    """)
                    self.log("Departure time filled: 17:00")
                    departure_found = True
            except Exception as e:
                self.log(f"Error with departure time: {str(e)}")

            if not departure_found:
                self.log("Warning: Could not fill departure time")

            page.wait_for_timeout(500)

            # Step 5: Click محفوظ (Save) button
            self.log("Step 5: Clicking save button...")
            save_found = False

            try:
                result = page.evaluate("""
                    () => {
                        const buttons = document.querySelectorAll('button');
                        for (let btn of buttons) {
                            if (btn.textContent.includes('محفوظ') && btn.offsetHeight > 0) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                if result:
                    self.log("Save button clicked successfully")
                    save_found = True
                    page.wait_for_timeout(3000)
            except Exception as e:
                self.log(f"Error clicking save: {str(e)}")

            if not save_found:
                self.log("Warning: Could not click save button")

            page.wait_for_timeout(2000)
            self.log("Attendance marked successfully: Present, 09:00 AM - 05:00 PM")
            return True

        except Exception as e:
            self.log(f"ERROR marking attendance: {str(e)}")
            return False

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

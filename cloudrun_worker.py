import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import re

async def deploy_via_sso(sso_url: str) -> str:
    parsed_url = urllib.parse.urlparse(sso_url)
    qs = urllib.parse.parse_qs(parsed_url.query)
    project_id = qs.get('project', [None])[0]

    if not project_id:
        raise ValueError("Project ID introuvable dans l'URL SSO.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1. Open SSO URL
            await page.goto(sso_url, timeout=60000)

            # 2. Detect and click Google terms accept buttons
            # "I understand" / "J'accepte" etc.
            # This is highly dependent on the exact Google prompt.
            # We'll try common selectors.
            try:
                await page.wait_for_selector('text="I understand"', timeout=5000)
                await page.click('text="I understand"')
            except Exception:
                pass

            try:
                await page.wait_for_selector('text="J\'accepte"', timeout=5000)
                await page.click('text="J\'accepte"')
            except Exception:
                pass

            # 3. Google Cloud TOS
            try:
                await page.wait_for_selector('mat-checkbox[formcontrolname="tos"]', timeout=10000)
                await page.click('mat-checkbox[formcontrolname="tos"]')
                await page.click('button:has-text("Agree and continue")')
            except Exception:
                pass

            # 4. Navigate to Cloud Run create
            create_url = f"https://console.cloud.google.com/run/create?project={project_id}"
            await page.goto(create_url, timeout=60000)

            # 5. Fill container image
            await page.wait_for_selector('input[placeholder*="image"]', timeout=30000)
            await page.fill('input[placeholder*="image"]', 'docker.io/gjndjd2/ahmed-vip1')

            # 6. Service name
            # Usually pre-filled from image name, but we can set it if needed.
            # Assuming it defaults to ahmed-vip1

            # 7. Region (us-central1 is usually default, but we should ensure)
            # 8. Authentication: Allow unauthenticated
            try:
                await page.click('text="Allow unauthenticated invocations"')
            except Exception:
                pass

            # 9. Ingress: All (Usually default)

            # 10. Click Create
            await page.click('button:has-text("Create")')

            # 11. Wait for URL
            # The URL usually appears with a link starting with https://ahmed-vip1
            await page.wait_for_selector('a[href^="https://ahmed-vip1"]', timeout=120000)
            url_element = await page.query_selector('a[href^="https://ahmed-vip1"]')
            cloudrun_url = await url_element.get_attribute('href')

            return cloudrun_url

        except Exception as e:
            raise Exception(f"Erreur lors du déploiement: {str(e)}")
        finally:
            await browser.close()

async def deploy_via_manual(project_id: str, email: str, password: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1. Login to Google
            await page.goto("https://accounts.google.com/")
            await page.fill('input[type="email"]', email)
            await page.click('button:has-text("Next")')

            await page.wait_for_selector('input[type="password"]', timeout=10000)
            await page.fill('input[type="password"]', password)
            await page.click('button:has-text("Next")')

            # Wait for login to complete
            await page.wait_for_url(re.compile(r"myaccount\.google\.com|console\.cloud\.google\.com"), timeout=30000)

            # Follow similar steps to SSO deployment
            # 3. Google Cloud TOS
            try:
                await page.goto("https://console.cloud.google.com/", timeout=30000)
                await page.wait_for_selector('mat-checkbox[formcontrolname="tos"]', timeout=10000)
                await page.click('mat-checkbox[formcontrolname="tos"]')
                await page.click('button:has-text("Agree and continue")')
            except Exception:
                pass

            # 4. Navigate to Cloud Run create
            create_url = f"https://console.cloud.google.com/run/create?project={project_id}"
            await page.goto(create_url, timeout=60000)

            # 5. Fill container image
            await page.wait_for_selector('input[placeholder*="image"]', timeout=30000)
            await page.fill('input[placeholder*="image"]', 'docker.io/gjndjd2/ahmed-vip1')

            # 8. Authentication: Allow unauthenticated
            try:
                await page.click('text="Allow unauthenticated invocations"')
            except Exception:
                pass

            # 10. Click Create
            await page.click('button:has-text("Create")')

            # 11. Wait for URL
            await page.wait_for_selector('a[href^="https://ahmed-vip1"]', timeout=120000)
            url_element = await page.query_selector('a[href^="https://ahmed-vip1"]')
            cloudrun_url = await url_element.get_attribute('href')

            return cloudrun_url

        except Exception as e:
            raise Exception(f"Erreur lors du déploiement: {str(e)}")
        finally:
            await browser.close()

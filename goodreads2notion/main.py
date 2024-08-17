import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def export_goodreads_library():
    """
    Use Selenium to get a new export of the user's data.
    """
    options = webdriver.ChromeOptions()

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        r"--user-data-dir=\"/mnt/c/Users/mdema/AppData/Local/Google/Chrome/User Data/Default\""
    )
    options.add_argument(r"--profile-directory=Default")

    service = ChromeService(
        executable_path=r"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    )
    driver = webdriver.Chrome(
        service=service,
        options=options,
    )

    # from selenium import webdriver
    # from selenium.webdriver.chrome.service import Service as ChromeService
    # options = webdriver.ChromeOptions()
    # service = ChromeService(executable_path=CHROMEDRIVER_PATH)
    # driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get("https://www.goodreads.com/review/import")

        export_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[text()='Export Library']"))
        )
        export_button.click()

        # wait up to 5 minutes for the export to be ready
        export_link = WebDriverWait(driver, 300).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//div[@id='exportFile']/following-sibling::br/following-sibling::a",
                )
            )
        )

        download_url = export_link.get_attribute("href")

        driver.get(download_url)

        time.sleep(10)

        downloads_path = os.path.expanduser("~/Downloads")
        for filename in os.listdir(downloads_path):
            if filename.startswith("goodreads_library_export"):
                old_path = os.path.join(downloads_path, filename)
                new_path = os.path.join(os.getcwd(), filename)
                os.rename(old_path, new_path)
                print(f"File saved as: {new_path}")
                break
        else:
            print("Export file not found in the Downloads folder.")

    finally:
        # Close the browser
        driver.quit()


if __name__ == "__main__":
    export_goodreads_library()

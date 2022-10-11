import os
import time
import zipfile
from contextlib import contextmanager

import requests
from attr import define
from bs4 import BeautifulSoup as BS
from dotenv import dotenv_values
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait


# initialize driver context
@contextmanager
def driver_context(config: 'Config'):
    os.makedirs(config.incomplete_downloads, exist_ok=True)
    chrome_options = Options()
    profile = {
        "download.default_directory": config.incomplete_downloads,
        "download.prompt_for_download": False,
        # "download_restrictions": 3
    }
    # chrome_options.add_argument('--disable-infobars')
    chrome_options.add_experimental_option("prefs", profile)
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--no-sandbox") # linux only
    # chrome_options.add_argument("--headless")
    chrome_options.binary_location = config.chrome_path
    # chrome_options.headless = True # also works
    driver = webdriver.Chrome(config.driver_path, options=chrome_options)
    try:
        yield driver
    finally:
        driver.quit()
        print('Quit')


def is_incomplete(filename):
    if '.com.brave.Browser' in filename:
        return True
    if filename.endswith('.crdownload'):
        return True
    return False


# waits for specified number of files to finish downloading from chromium driver
def wait_downloads(downloads_dir, timeout=None, nfiles=None):
    start_time = time.time()
    while not timeout or time.time() - start_time < timeout:
        time.sleep(min(max(time.time() - start_time, 0), 0.5))
        files = os.listdir(downloads_dir)
        print(f'Waiting downloads... {files}')
        if nfiles and len(files) != nfiles:
            continue
        if not any(is_incomplete(f) for f in files):
            return files
    return []


def wait_el(css_sel, driver, timeout=20, poll=0.5):
    return wait(driver, timeout=timeout, poll_frequency=poll).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css_sel)))


def wait_all(css_sel, driver, timeout=20, poll=0.5):
    return wait(driver, timeout=timeout, poll_frequency=poll).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_sel)))


def wait_clickable(css_sel, driver, timeout=20, poll=0.5):
    return wait(driver, timeout=timeout, poll_frequency=poll).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, css_sel)))


# switches to iframe automatically
# to switch back from iframe: driver.switch_to.default_content()
def wait_iframe(css_sel, driver, timeout=20, poll=0.5):
    return wait(driver, timeout=timeout, poll_frequency=poll).until(
        EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, css_sel)))


def login(driver, config: 'Config'):
    driver.get(f"{config.fer}/login/")
    print('Fetched fer.unizg.hr')

    user_in = wait_el('input#username', driver)
    user_in.send_keys(config.username)
    print('Entered username')

    pass_in = wait_el('input#password', driver)
    pass_in.send_keys(config.password)
    print('Entered password')

    submit = wait_el('button[type=submit]', driver)
    submit.click()
    print('Clicked submit login form')


@define(kw_only=True)
class Course:
    url: str
    name: str


def get_course_list(driver) -> list[Course]:
    el = wait_el('div.course_list_for_user', driver).get_attribute('innerHTML')
    soup = BS(el, 'lxml')
    courses = []
    for course in soup.find_all('a'):
        courses.append(Course(
            url=course.get('href'),
            name=course.text.strip()
        ))
    return courses


# skida sve materijale za taj predmet
def download_course_materials(course: Course, driver, config: 'Config'):
    print(f'--- Downloading materials for {course.name} ---')
    driver.get(f'{config.fer}{course.url}/materijali')
    cms_area = wait_el('#cms_area_middle', driver)
    cms_area_items = list(BS(cms_area.get_attribute('innerHTML'), 'lxml').children)
    if not cms_area_items:
        print(cms_area_items)
        print('No files to download')
        return

    folders = driver.find_elements(By.CSS_SELECTOR, '.resultitemFolder')
    for folder in folders:
        el = folder.find_element(By.CSS_SELECTOR, '.name')
        name = el.get_attribute("innerHTML").strip()
        print(f'Folder {name}')
        wait_clickable('.downloadZipFile', driver).click()
        print('Clicked prepare download')
        wait_iframe('iframe', driver)
        print('Focus iframe')
        dls = wait_downloads(config.incomplete_downloads, nfiles=1)
        print(f'Awaited downloads: {dls}')
        assert len(dls) == 1
        # url = wait_clickable('a#download_link', driver).get_attribute('href').replace('blob:', '')
        source = f'{config.incomplete_downloads}/{dls[0]}'
        destination = f'{config.destination}/{course.name}/materijali/{name}'
        os.makedirs(destination, exist_ok=True)  # ensure dir
        with zipfile.ZipFile(source, 'r') as zip_ref:
            zip_ref.extractall(destination)
        os.remove(source)
        driver.switch_to.default_content()
        print('Unfocus iframe')
        wait_clickable('.ui-dialog-buttonset > button[type=button]', driver).click()
        print('Closed dialog')

    files = driver.find_elements(By.CSS_SELECTOR, ".resultitemFile")
    for file in files:
        name = file.find_element(By.CSS_SELECTOR, '.name').get_attribute('innerHTML').strip()
        source = file.find_element(By.CSS_SELECTOR, 'a[href]').get_attribute('href')
        _, ext = os.path.splitext(source)
        destination = f'{config.destination}/{course.name}/materijali/{name}.{ext}'
        if not ext:
            print(f'{source} file extension not present...')
            continue
        r = requests.get(source, auth=(config.username, config.password))
        if r.status_code != 200:
            print(f'Received status code {r.status_code} for file {source}')
            r.close()
        with open(destination, 'wb') as out:
            for bits in r.iter_content():
                out.write(bits)


@define(kw_only=True)
class Config:
    fer: str
    username: str
    password: str
    chrome_path: str
    driver_path: str
    incomplete_downloads: str
    destination: str


def try_configs(*paths):
    for path in paths:
        if os.path.isfile(path):
            return dotenv_values(path)


def main():
    env = try_configs('.env', '.example.env')
    env = {k.lower(): v for k, v in env.items()}
    config = Config(**env)
    config.incomplete_downloads = os.path.abspath(config.incomplete_downloads)
    config.destination = os.path.abspath(config.destination)

    with driver_context(config) as driver:
        login(driver, config)
        wait_el("a[href='/intranet']", driver)
        driver.get(f'{config.fer}/intranet')
        courses = get_course_list(driver)
        for course in courses:
            download_course_materials(course, driver, config)
        print(courses)


if __name__ == '__main__':
    main()

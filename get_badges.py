import requests
import getpass
import csv
import datetime
import time
from collections import OrderedDict
from bs4 import BeautifulSoup
import os

session = requests.Session()
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

def ask_credentials():
    print('Your Codecademy Credentials:')
    email = input('Username or Email: ')
    password = getpass.getpass()
    return {
        "login": email,
        "password": password
    }

def get_with_chrome(url, css_selector):
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException

    browser = webdriver.Chrome()
    browser.get(url)
    delay = 3 # seconds
    try:
        myElem = WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
        print("Page is ready!")
    except TimeoutException:
        print("Loading took too much time!")

    inner_html = browser.execute_script("return document.body.innerHTML") #returns the inner HTML as a string
    # print(inner_html)
    cookies_list = browser.get_cookies()
    cookies_dict = {}
    for cookie in cookies_list:
        cookies_dict[cookie['name']] = cookie['value']

    # cookies = browser.get_cookies();
    # print(cookies_dict)
    browser.close()
    return {
        'html': inner_html,
        'cookies': cookies_dict
    }

def login(credentials):
    url = 'https://www.codecademy.com/login'
    response = session.get(url, headers=headers)
    if response.status_code!=200:
        print('Error: Could not get codecademy home page')
        print(response.text)
        return False

    def get_authenticity_token(soup):
        form_tag = soup.find('form', {'action': '/login'})
        authenticity_token_tag = form_tag.find('input', {'name': 'authenticity_token'})
        authenticity_token = authenticity_token_tag['value']
        return authenticity_token

    try:
        soup = BeautifulSoup(response.text, "html.parser")
        authenticity_token = get_authenticity_token(soup)
    except AttributeError:
        result = get_with_chrome(url, 'input[name="authenticity_token"]')
        soup = BeautifulSoup(result['html'], "html.parser")
        session.cookies.update(result['cookies'])
        authenticity_token = get_authenticity_token(soup)

    if not authenticity_token:
        print('Could not determine authenticity token')
        return False

    response = session.post('https://www.codecademy.com/login', data={
        'user[login]': credentials['login'],
        'user[password]': credentials['password'],
        'authenticity_token': authenticity_token,
        'redirect': ''
    })
    if 'remember_user_token' in session.cookies:
        print('Logged In')
        return True
    else:
        print('Could not login')
        return False

def get_badges():
    checklist = get_checklist()
    results_list = []
    for user in get_users():
        result = {
            'username': (user['username'] or '').strip(),
            'name': (user['name'] or '').strip()
        }
        if user['username']:
            get_achievements(user, checklist, result)

        results_list.append(result)

        time.sleep(1)

    save_user_badges(results_list, checklist)

def get_users():
    users = []
    with open(os.path.join('data', 'user_list.csv'), 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        users = list(reader)
    return users

def get_checklist():
    badges = OrderedDict()
    with open(os.path.join('data', 'checklist.csv'), 'r') as checklist_file:
        reader = csv.DictReader(checklist_file)
        for row in reader:
            badges[row['badge']] = datetime.datetime.strptime(row['due_date'], '%m/%d/%Y')

    return badges

def get_achievements(user, checklist, result):
    achievements_url = "https://www.codecademy.com/users/{0}/achievements".format(user['username'])
    response = session.get(achievements_url)
    if response.status_code==200:
        soup = BeautifulSoup(response.text, "html.parser")
        achievement_cards = soup.find_all('div', {'class': 'achievement-card'})
        for card in achievement_cards:
            achievement_title = (card.find('h5').text
                .replace('Course Completed: Learn ', '')
                # .replace('Lesson Completed: Learn ', '')
                .replace('Course Completed: ', '')
                # .replace('Lesson Completed: ', '')
            )
            achievement_date_text = card.find('small', {'class': 'text--ellipsis'}).text
            achievement_date = datetime.datetime.strptime(achievement_date_text, "%b %d, %Y")
            if achievement_title in checklist:
                if achievement_date <= checklist[achievement_title]:
                    result[achievement_title] = "Done"
                else:
                    result[achievement_title] = achievement_date.strftime("%d %b")

def save_user_badges(results_list, checklist):
    with open(os.path.join('data', 'results.csv'), 'w') as results_file:
        fieldnames = ['name', 'username'] + list(checklist.keys())
        writer = csv.DictWriter(results_file, fieldnames)
        writer.writeheader()
        for result in results_list:
            writer.writerow(result)

    print('File updated: results.csv')

if __name__=="__main__":
    credentials = ask_credentials()
    login_success = login(credentials)
    if login_success:
        get_badges()

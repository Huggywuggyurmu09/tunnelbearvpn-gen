import requests
import time
import re
import random
import string
import threading
from concurrent.futures import ThreadPoolExecutor

write_lock = threading.Lock()

def load_proxies(filename="proxies.txt"):
    try:
        with open(filename, "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
        return proxies
    except Exception as e:
        print("Error reading proxies file:", e)
        return []

def save_credentials(email, password, proxy=None):
    line = f"{email}:{password}"
    line += "\n"
    with write_lock:
        try:
            with open("accs.txt", "a") as f:
                f.write(line)
            print("Credentials saved:", line.strip())
        except Exception as e:
            print("Error saving credentials:", e)

def create_temp_inbox(session):
    url = 'https://api.tempmail.lol/v2/inbox/create'
    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'DNT': '1',
        'Origin': 'https://tempmail.lol',
        'Referer': 'https://tempmail.lol/',
        'User-Agent': 'Mozilla/5.0'
    }
    payload = {"captcha": None, "domain": None, "prefix": ""}
    try:
        response = session.post(url, headers=headers, json=payload, timeout=10)
        print("DEBUG: create_temp_inbox: HTTP", response.status_code)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error in create_temp_inbox:", e)
        try:
            print("Response content:", response.text)
        except Exception:
            pass
        return None

def check_inbox(session, token):
    url = f'https://api.tempmail.lol/v2/inbox?token={token}'
    headers = {
        'Accept': '*/*',
        'DNT': '1',
        'Origin': 'https://tempmail.lol',
        'Referer': 'https://tempmail.lol/',
        'User-Agent': 'Mozilla/5.0'
    }
    try:
        response = session.get(url, headers=headers, timeout=10)
        print("DEBUG: check_inbox: HTTP", response.status_code)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error in check_inbox:", e)
        return None

def generate_password():
    uppercase = random.choice(string.ascii_uppercase)
    letters = ''.join(random.choices(string.ascii_lowercase, k=6))
    special = random.choice("!@#$%^&*()-_=+")
    password_list = list(uppercase + letters + special)
    random.shuffle(password_list)
    password = ''.join(password_list)
    print("DEBUG: Generated password:", password)
    return password

def send_tunnelbear_create_account(session, email, password):
    url = "https://prod-api-core.tunnelbear.com/core/web/createAccount"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.5",
        "Alt-Used": "prod-api-core.tunnelbear.com",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        "Cookie": (""),
        "DNT": "1",
        "Host": "prod-api-core.tunnelbear.com",
        "Origin": "https://www.tunnelbear.com",
        "Pragma": "no-cache",
        "Priority": "u=4",
        "Referer": "https://www.tunnelbear.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
        "TB-CSRF-Token": "",
        "TE": "trailers",
        "tunnelbear-app-id": "com.tunnelbear.web",
        "tunnelbear-app-version": "1.0.0",
        "tunnelbear-platform": "Firefox",
        "tunnelbear-platform-version": "138",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0"
    }
    
    payload = {
        "email": email,
        "password": password,
        "json": "1",
        "v": "web-1.0",
        "referralKey": "",
        "tbaa_utm_source": "website"
    }
    
    try:
        response = session.post(url, headers=headers, data=payload, timeout=10)
        print("DEBUG: send_tunnelbear_create_account: HTTP", response.status_code)
        print("DEBUG: TunnelBear account creation response:", response.text)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error in send_tunnelbear_create_account:", e)
        try:
            print("Response content:", response.text)
        except Exception:
            pass
        return None

def extract_verification_links(content):
    pattern = r'https://api\.tunnelbear\.com/core/verifyEmail\?key=[\w-]+'
    links = re.findall(pattern, content)
    return links

def process_verification_link(session, link):
    try:
        v_response = session.get(link, timeout=10)
        status = v_response.status_code
        print(f"GET {link} returned HTTP {status}")
        with write_lock:
            with open("genned.txt", "a") as f:
                f.write(f"{link}: HTTP {status}\n")
        return (status == 200)
    except Exception as e:
        print(f"Error accessing link {link}: {e}")
    return False

def worker(task_id, proxies_list):
    session = requests.Session()
    chosen_proxy = None
    if proxies_list:
        chosen_proxy = random.choice(proxies_list)
        session.proxies = {
            "http": f"http://{chosen_proxy}",
            "https": f"http://{chosen_proxy}"
        }
        print(f"[Task {task_id}] Using proxy: {chosen_proxy}")

    temp_data = create_temp_inbox(session)
    if not temp_data:
        print(f"[Task {task_id}] Failed to create temporary inbox.")
        return

    email_address = temp_data.get('address')
    token = temp_data.get('token')
    if not email_address or not token:
        print(f"[Task {task_id}] Incomplete data from temporary inbox.")
        return

    print(f"[Task {task_id}] Temporary Email Generated: {email_address}")

    password = generate_password()
    tb_response = send_tunnelbear_create_account(session, email_address, password)
    if tb_response is not None:
        print(f"[Task {task_id}] TunnelBear account creation response received.")
    else:
        print(f"[Task {task_id}] Failed to create account with TunnelBear.")
    save_credentials(email_address, password, chosen_proxy)

    processed_links = set()
    verified = False
    print(f"[Task {task_id}] Starting inbox check for verification link...")
    while not verified:
        inbox = check_inbox(session, token)
        if inbox:
            emails = inbox.get('emails', [])
            if emails:
                print(f"[Task {task_id}] Found {len(emails)} email(s) in inbox.")
            for email in emails:
                content = email.get('html') or email.get('body', '')
                links = extract_verification_links(content)
                for link in links:
                    if link in processed_links:
                        continue
                    print(f"[Task {task_id}] Processing verification link: {link}")
                    processed_links.add(link)
                    if process_verification_link(session, link):
                        verified = True
                        break
                if verified:
                    break
        else:
            print(f"[Task {task_id}] Failed to retrieve inbox data.")
        if not verified:
            time.sleep(2)
    print(f"[Task {task_id}] Account {email_address} verified. Stopping inbox checks.")

if __name__ == '__main__':
    try:
        num_accounts = int(input("How many accounts to generate: "))
    except ValueError:
        print("Invalid input. Please enter an integer.")
        exit(1)

    proxies_list = load_proxies()

    with ThreadPoolExecutor(max_workers=num_accounts) as executor:
        futures = []
        for i in range(num_accounts):
            futures.append(executor.submit(worker, i + 1, proxies_list))
        for future in futures:
            future.result()

    print("All account tasks completed.")

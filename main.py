import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
from textblob import TextBlob
import random
import re
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from threading import Thread
import time
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import calendar
from dateutil.parser import parse

# Download NLTK data
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('stopwords')

class TodoApp:
    def __init__(self):
        # Initialize database
        self.initialize_database()
        
        # Email configuration (replace with your SMTP details)
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email_sender = "labannya38@gmail.com"
        self.email_password = "vhtk fxxh poqn vlpa"
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("AI To-Do List")
        self.root.geometry("1000x700")
        
        # Initialize NLP components
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # Show login screen
        self.show_login_screen()
        
        # Start background notification thread
        self.notification_thread_running = True
        Thread(target=self.notification_daemon, daemon=True).start()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()
    
    def on_close(self):
        self.notification_thread_running = False
        self.root.destroy()
    
    def initialize_database(self):
        self.conn = sqlite3.connect('todo_app.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Create users table if not exists
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                notify_enabled BOOLEAN DEFAULT 1,
                notify_before_days INTEGER DEFAULT 1,
                notify_time TEXT DEFAULT "09:00",
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create tasks table if not exists
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                priority TEXT NOT NULL,
                task TEXT NOT NULL,
                due_date TEXT,
                category TEXT NOT NULL,
                time_estimate INTEGER NOT NULL,
                completed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        self.conn.commit()
    
    def hash_password(self, password):
        """Consistent SHA-256 hashing for both registration and login"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def show_login_screen(self):
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Login frame
        login_frame = tk.Frame(self.root)
        login_frame.pack(pady=50)
        
        # Title
        tk.Label(login_frame, text="AI To-Do List", font=("Arial", 24)).grid(row=0, column=0, columnspan=2, pady=20)
        
        # Username
        tk.Label(login_frame, text="Username:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.username_entry = tk.Entry(login_frame, width=30)
        self.username_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Password
        tk.Label(login_frame, text="Password:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.password_entry = tk.Entry(login_frame, width=30, show="*")
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Login button
        tk.Button(login_frame, text="Login", command=self.login).grid(row=3, column=0, columnspan=2, pady=10)
        
        # Register link
        tk.Label(login_frame, text="Don't have an account?", fg="blue").grid(row=4, column=0, columnspan=2)
        register_label = tk.Label(login_frame, text="Register here", fg="blue", cursor="hand2")
        register_label.grid(row=5, column=0, columnspan=2)
        register_label.bind("<Button-1>", lambda e: self.show_register_screen())
    
    def show_register_screen(self):
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Register frame
        register_frame = tk.Frame(self.root)
        register_frame.pack(pady=50)
        
        # Title
        tk.Label(register_frame, text="Register", font=("Arial", 24)).grid(row=0, column=0, columnspan=2, pady=20)
        
        # Username
        tk.Label(register_frame, text="Username:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.reg_username_entry = tk.Entry(register_frame, width=30)
        self.reg_username_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Email
        tk.Label(register_frame, text="Email:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.reg_email_entry = tk.Entry(register_frame, width=30)
        self.reg_email_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Password
        tk.Label(register_frame, text="Password:").grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.reg_password_entry = tk.Entry(register_frame, width=30, show="*")
        self.reg_password_entry.grid(row=3, column=1, padx=5, pady=5)
        
        # Confirm Password
        tk.Label(register_frame, text="Confirm Password:").grid(row=4, column=0, sticky='e', padx=5, pady=5)
        self.reg_confirm_password_entry = tk.Entry(register_frame, width=30, show="*")
        self.reg_confirm_password_entry.grid(row=4, column=1, padx=5, pady=5)
        
        # Register button
        tk.Button(register_frame, text="Register", command=self.register).grid(row=5, column=0, columnspan=2, pady=10)
        
        # Back to login
        tk.Button(register_frame, text="Back to Login", command=self.show_login_screen).grid(row=6, column=0, columnspan=2, pady=10)
    
    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        hashed_password = self.hash_password(password)
        
        try:
            # Case-insensitive username comparison
            self.cursor.execute("""
                SELECT id, username, email FROM users 
                WHERE username=? AND password=?
            """, (username, hashed_password))
            user = self.cursor.fetchone()
            
            if user:
                self.current_user = {
                    "id": user[0],
                    "username": user[1],
                    "email": user[2]
                }
                self.show_main_app()
            else:
                # More detailed error message
                self.cursor.execute("SELECT username FROM users WHERE username=?", (username,))
                if self.cursor.fetchone():
                    messagebox.showerror("Error", "Incorrect password")
                else:
                    messagebox.showerror("Error", "Username not found")
        except Exception as e:
            messagebox.showerror("Database Error", f"Login failed: {str(e)}")
            print(f"Login error: {e}")
    
    def register(self):
        username = self.reg_username_entry.get().strip()
        email = self.reg_email_entry.get().strip()
        password = self.reg_password_entry.get().strip()
        confirm_password = self.reg_confirm_password_entry.get().strip()
        
        if not username or not email or not password or not confirm_password:
            messagebox.showerror("Error", "All fields are required")
            return
        
        if password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match")
            return
        
        if len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters")
            return
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messagebox.showerror("Error", "Invalid email address")
            return
        
        hashed_password = self.hash_password(password)
        
        try:
            self.cursor.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", 
                              (username, hashed_password, email))
            self.conn.commit()
            messagebox.showinfo("Success", "Registration successful! Please login.")
            self.show_login_screen()
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                messagebox.showerror("Error", "Username already exists")
            elif "email" in str(e):
                messagebox.showerror("Error", "Email already registered")
    
    def show_main_app(self):
        # Clear existing widgets
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Create menu bar
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Logout", command=self.logout)
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Notification Settings", command=self.show_notification_settings)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        
        self.root.config(menu=menubar)
        
        # Frame for task input
        input_frame = tk.Frame(self.root)
        input_frame.pack(pady=10)
        
        # Natural language input
        tk.Label(input_frame, text="Enter task:").grid(row=0, column=0, sticky='w')
        self.task_entry = tk.Entry(input_frame, width=50)
        self.task_entry.grid(row=1, column=0, columnspan=3, pady=5, sticky='ew')
        
        # Due date input with calendar button
        tk.Label(input_frame, text="Due Date:").grid(row=2, column=0, sticky='w')
        
        self.due_date_var = tk.StringVar()
        self.due_date_entry = tk.Entry(input_frame, width=15, textvariable=self.due_date_var)
        self.due_date_entry.grid(row=3, column=0, sticky='w')
        
        # Calendar button
        calendar_btn = tk.Button(input_frame, text="📅", command=self.show_calendar)
        calendar_btn.grid(row=3, column=1, sticky='w', padx=5)
        
        tk.Label(input_frame, text="Format: YYYY-MM-DD").grid(row=3, column=2, sticky='w')
        
        # Add task button
        add_button = tk.Button(input_frame, text="Add Task", command=self.add_task_from_nlp)
        add_button.grid(row=4, column=0, pady=10, sticky='ew', columnspan=3)
        
        # Task list
        self.task_tree = ttk.Treeview(self.root, columns=("Priority", "Task", "Due Date", "Days Left", "Category", "Time Estimate"), show="headings")
        
        # Configure columns
        columns = {
            "Priority": {"width": 80, "anchor": "center"},
            "Task": {"width": 200},
            "Due Date": {"width": 100, "anchor": "center"},
            "Days Left": {"width": 80, "anchor": "center"},
            "Category": {"width": 100, "anchor": "center"},
            "Time Estimate": {"width": 80, "anchor": "center"}
        }
        
        for col, config in columns.items():
            self.task_tree.heading(col, text=col, command=lambda c=col: self.sort_tasks(c))
            self.task_tree.column(col, **config)
        
        self.task_tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # Buttons frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        # Complete button
        complete_button = tk.Button(button_frame, text="Mark Complete", command=self.mark_complete)
        complete_button.grid(row=0, column=0, padx=5)
        
        # Delete button
        delete_button = tk.Button(button_frame, text="Delete Task", command=self.delete_task)
        delete_button.grid(row=0, column=1, padx=5)
        
        # AI suggestions button
        suggest_button = tk.Button(button_frame, text="AI Suggestions", command=self.generate_ai_suggestions)
        suggest_button.grid(row=0, column=2, padx=5)
        
        # Smart schedule button
        schedule_button = tk.Button(button_frame, text="Smart Schedule", command=self.smart_schedule)
        schedule_button.grid(row=0, column=3, padx=5)
        
        # Edit button
        edit_button = tk.Button(button_frame, text="Edit Task", command=self.edit_task)
        edit_button.grid(row=0, column=4, padx=5)
        
        # Load user's tasks
        self.refresh_task_list()
    
    def logout(self):
        self.current_user = None
        self.show_login_screen()
    
    def show_notification_settings(self):
        # Get current notification settings
        self.cursor.execute("SELECT notify_enabled, notify_before_days, notify_time FROM users WHERE id=?", (self.current_user["id"],))
        settings = self.cursor.fetchone()
        
        notify_enabled = settings[0] if settings and settings[0] is not None else 1
        notify_before_days = settings[1] if settings and settings[1] is not None else 1
        notify_time = settings[2] if settings and settings[2] is not None else "09:00"
        
        # Create settings window
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Notification Settings")
        
        # Notification enabled checkbox
        self.notify_enabled_var = tk.IntVar(value=notify_enabled)
        tk.Checkbutton(settings_win, text="Enable Email Notifications", variable=self.notify_enabled_var).grid(row=0, column=0, columnspan=2, sticky='w', pady=5)
        
        # Days before notification
        tk.Label(settings_win, text="Notify before due date (days):").grid(row=1, column=0, sticky='w', pady=5)
        self.notify_before_days_var = tk.StringVar(value=str(notify_before_days))
        tk.Entry(settings_win, width=5, textvariable=self.notify_before_days_var).grid(row=1, column=1, sticky='w', pady=5)
        
        # Notification time
        tk.Label(settings_win, text="Notification time (HH:MM):").grid(row=2, column=0, sticky='w', pady=5)
        self.notify_time_var = tk.StringVar(value=notify_time)
        tk.Entry(settings_win, width=5, textvariable=self.notify_time_var).grid(row=2, column=1, sticky='w', pady=5)
        
        # Save button
        tk.Button(settings_win, text="Save Settings", command=lambda: self.save_notification_settings(settings_win)).grid(row=3, column=0, columnspan=2, pady=10)
    
    def save_notification_settings(self, window):
        try:
            notify_before_days = int(self.notify_before_days_var.get())
            if notify_before_days < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of days")
            return
        
        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", self.notify_time_var.get()):
            messagebox.showerror("Error", "Please enter time in HH:MM format")
            return
        
        self.cursor.execute('''
            UPDATE users SET 
                notify_enabled = ?,
                notify_before_days = ?,
                notify_time = ?
            WHERE id = ?
        ''', (
            self.notify_enabled_var.get(),
            notify_before_days,
            self.notify_time_var.get(),
            self.current_user["id"]
        ))
        self.conn.commit()
        messagebox.showinfo("Success", "Notification settings saved")
        window.destroy()
    
    def notification_daemon(self):
        while self.notification_thread_running:
            time.sleep(60)  # Check every minute
            
            if not hasattr(self, 'current_user'):
                continue
                
            # Get user's notification settings
            self.cursor.execute('''
                SELECT notify_enabled, notify_before_days, notify_time, email 
                FROM users WHERE id=?
            ''', (self.current_user["id"],))
            settings = self.cursor.fetchone()
            
            if not settings or not settings[0]:  # Notifications disabled
                continue
            
            notify_before_days = settings[1]
            notify_time = settings[2]
            user_email = settings[3]
            
            # Check if it's the right time to send notifications
            current_time = datetime.now().strftime("%H:%M")
            if current_time != notify_time:
                continue
            
            # Get tasks that are due soon
            due_date = (datetime.now() + timedelta(days=notify_before_days)).strftime("%Y-%m-%d")
            
            self.cursor.execute('''
                SELECT task, due_date FROM tasks 
                WHERE user_id=? AND completed=0 AND due_date <= ? AND due_date >= date('now')
                ORDER BY due_date
            ''', (self.current_user["id"], due_date))
            upcoming_tasks = self.cursor.fetchall()
            
            if not upcoming_tasks:
                continue
            
            # Prepare email
            subject = f"Upcoming Tasks Notification ({len(upcoming_tasks)} tasks)"
            
            message_lines = [f"You have {len(upcoming_tasks)} upcoming tasks:"]
            for task in upcoming_tasks:
                days_left = (datetime.strptime(task[1], "%Y-%m-%d") - datetime.now()).days
                message_lines.append(f"- {task[0]} (Due: {task[1]}, {days_left} days left)")
            
            message = "\n".join(message_lines)
            
            # Send email in background
            Thread(target=self.send_email, args=(user_email, subject, message), daemon=True).start()
    
    def send_email(self, recipient, subject, message):
        try:
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = self.email_sender
            msg['To'] = recipient
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_sender, self.email_password)
                server.sendmail(self.email_sender, [recipient], msg.as_string())
        except Exception as e:
            print(f"Failed to send email: {e}")
    
    def show_calendar(self):
        """Show a simple calendar popup for date selection"""
        top = tk.Toplevel(self.root)
        top.title("Select Due Date")
        
        today = datetime.now()
        year = today.year
        month = today.month
        
        def set_date(day):
            self.due_date_var.set(f"{year}-{month:02d}-{day:02d}")
            top.destroy()
        
        # Month navigation
        nav_frame = tk.Frame(top)
        nav_frame.pack(pady=5)
        
        def change_month(delta):
            nonlocal month, year
            month += delta
            if month > 12:
                month = 1
                year += 1
            elif month < 1:
                month = 12
                year -= 1
            update_calendar()
        
        tk.Button(nav_frame, text="<", command=lambda: change_month(-1)).pack(side=tk.LEFT)
        month_label = tk.Label(nav_frame, text=f"{self.get_month_name(month)} {year}")
        month_label.pack(side=tk.LEFT)
        tk.Button(nav_frame, text=">", command=lambda: change_month(1)).pack(side=tk.LEFT)
        
        # Calendar
        cal_frame = tk.Frame(top)
        cal_frame.pack()
        
        # Weekday headers
        for i, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            tk.Label(cal_frame, text=day, width=4).grid(row=0, column=i)
        
        self.cal_labels = []
        
        def update_calendar():
            month_label.config(text=f"{self.get_month_name(month)} {year}")
            
            # Clear existing labels
            for label_row in self.cal_labels:
                for label in label_row:
                    label.grid_forget()
            self.cal_labels.clear()
            
            # Get month calendar
            cal = calendar.Calendar()
            month_days = cal.monthdayscalendar(year, month)
            
            # Create new labels
            for week_num, week in enumerate(month_days, start=1):
                week_labels = []
                for day_num, day in enumerate(week):
                    if day == 0:
                        lbl = tk.Label(cal_frame, text="", width=4)
                    else:
                        lbl = tk.Button(cal_frame, text=str(day), width=4,
                                      command=lambda d=day: set_date(d))
                        # Highlight today
                        if day == today.day and month == today.month and year == today.year:
                            lbl.config(bg='lightblue')
                    lbl.grid(row=week_num, column=day_num)
                    week_labels.append(lbl)
                self.cal_labels.append(week_labels)
        
        update_calendar()
    
    def get_month_name(self, month):
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        return months[month - 1]
    
    def add_task_from_nlp(self):
        task_text = self.task_entry.get().strip()
        if not task_text:
            messagebox.showwarning("Warning", "Please enter a task")
            return
        
        # Get due date from input field
        due_date_input = self.due_date_var.get().strip()
        
        # Process with NLP
        task_details = self.process_natural_language(task_text, due_date_input)
        
        # Add to database
        self.cursor.execute('''
            INSERT INTO tasks (user_id, priority, task, due_date, category, time_estimate)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            self.current_user["id"],
            task_details["Priority"],
            task_details["Task"],
            task_details["Due Date"],
            task_details["Category"],
            task_details["Time Estimate"]
        ))
        self.conn.commit()
        
        self.refresh_task_list()
        self.task_entry.delete(0, tk.END)
        self.due_date_var.set("")
    
    def process_natural_language(self, text, due_date_input=""):
        blob = TextBlob(text)
        tokens = nltk.word_tokenize(text.lower())
        filtered_tokens = [self.lemmatizer.lemmatize(w) for w in tokens if w not in self.stop_words]
        
        # Priority detection
        priority = "Medium"
        priority_scores = {"High": 0, "Medium": 0, "Low": 0}
        priority_keywords = {
            "High": ["urgent", "important", "asap", "critical", "deadline", "must"],
            "Medium": ["should", "review", "check", "follow up"],
            "Low": ["whenever", "optional", "someday", "if time"]
        }
        
        for word in filtered_tokens:
            for level, keywords in priority_keywords.items():
                if word in keywords:
                    priority_scores[level] += 1
        
        max_score = max(priority_scores.values())
        if max_score > 0:
            priority = [k for k, v in priority_scores.items() if v == max_score][0]
        
        # Date parsing
        due_date = ""
        try:
            if due_date_input:
                due_date = parse(due_date_input, fuzzy=True).strftime('%Y-%m-%d')
            else:
                date_patterns = [
                    r'\b(today|now)\b',
                    r'\b(tomorrow)\b',
                    r'\b(next week|next month)\b',
                    r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
                    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}\b'
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        due_date = parse(match.group(), fuzzy=True).strftime('%Y-%m-%d')
                        break
        except:
            pass
        
        # Category detection
        category = "General"
        categories = {
            "Work": ["work", "job", "office", "meeting", "project", "report", "presentation"],
            "Personal": ["personal", "family", "home", "friend", "gift", "birthday"],
            "Health": ["exercise", "gym", "doctor", "health", "yoga", "medic", "appointment"],
            "Finance": ["bill", "pay", "tax", "invoice", "budget", "bank"],
            "Learning": ["study", "read", "learn", "course", "book", "research"]
        }
        
        for cat, keywords in categories.items():
            if any(keyword in filtered_tokens for keyword in keywords):
                category = cat
                break
        
        # Time estimation
        time_estimate = 30  # default 30 minutes
        time_keywords = {
            "quick": 15,
            "fast": 15,
            "short": 15,
            "long": 120,
            "extensive": 240,
            "hour": 60,
            "hours": lambda x: int(x) * 60 if x.isdigit() else 60
        }
        
        for i, word in enumerate(filtered_tokens):
            if word in time_keywords:
                if callable(time_keywords[word]):
                    if i > 0 and filtered_tokens[i-1].isdigit():
                        time_estimate = time_keywords[word](filtered_tokens[i-1])
                else:
                    time_estimate = time_keywords[word]
        
        return {
            "Priority": priority,
            "Task": text,
            "Due Date": due_date,
            "Category": category,
            "Time Estimate": time_estimate
        }
    
    def refresh_task_list(self):
        # Clear current items
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        # Get tasks from database
        self.cursor.execute('''
            SELECT id, priority, task, due_date, category, time_estimate 
            FROM tasks 
            WHERE user_id=? AND completed=0
            ORDER BY 
                CASE priority 
                    WHEN 'High' THEN 1 
                    WHEN 'Medium' THEN 2 
                    WHEN 'Low' THEN 3 
                    ELSE 4 
                END,
                due_date IS NULL,
                due_date
        ''', (self.current_user["id"],))
        tasks = self.cursor.fetchall()
        
        # Add tasks to treeview with color coding
        today = datetime.now().date()
        
        for task in tasks:
            task_id = task[0]
            priority = task[1]
            task_text = task[2]
            due_date = task[3]
            category = task[4]
            time_estimate = task[5]
            
            tags = ()
            if priority == "High":
                tags = ('high',)
            elif priority == "Low":
                tags = ('low',)
            
            # Calculate days left
            days_left = ""
            if due_date:
                try:
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                    delta = (due_date_obj - today).days
                    days_left = str(delta)
                    if delta < 0:
                        tags += ('overdue',)
                    elif delta == 0:
                        tags += ('due-today',)
                    elif delta <= 3:
                        tags += ('due-soon',)
                except:
                    pass
            
            self.task_tree.insert("", tk.END, iid=task_id, values=(
                priority,
                task_text,
                due_date if due_date else "",
                days_left,
                category,
                f"{time_estimate} min"
            ), tags=tags)
        
        # Configure tag colors
        self.task_tree.tag_configure('high', background='#ffcccc')
        self.task_tree.tag_configure('low', background='#ccffcc')
        self.task_tree.tag_configure('overdue', background='#ff9999')
        self.task_tree.tag_configure('due-today', background='#ffff99')
        self.task_tree.tag_configure('due-soon', background='#ffeb99')
    
    def mark_complete(self):
        selected = self.task_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a task")
            return
        
        # Mark as complete in database
        for task_id in selected:
            self.cursor.execute("UPDATE tasks SET completed=1 WHERE id=?", (task_id,))
        self.conn.commit()
        
        self.refresh_task_list()
    
    def delete_task(self):
        selected = self.task_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a task")
            return
        
        if messagebox.askyesno("Confirm", "Are you sure you want to delete the selected task(s)?"):
            for task_id in selected:
                self.cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            self.conn.commit()
            self.refresh_task_list()
    
    def edit_task(self):
        selected = self.task_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a task to edit")
            return
        
        task_id = selected[0]
        
        # Get task details from database
        self.cursor.execute('''
            SELECT priority, task, due_date, category, time_estimate 
            FROM tasks WHERE id=?
        ''', (task_id,))
        task = self.cursor.fetchone()
        
        if not task:
            return
        
        # Create edit window
        edit_win = tk.Toplevel(self.root)
        edit_win.title("Edit Task")
        
        # Task description
        tk.Label(edit_win, text="Task:").grid(row=0, column=0, sticky='w')
        task_entry = tk.Entry(edit_win, width=50)
        task_entry.grid(row=0, column=1, padx=5, pady=5)
        task_entry.insert(0, task[1])
        
        # Due date
        tk.Label(edit_win, text="Due Date:").grid(row=1, column=0, sticky='w')
        due_date_entry = tk.Entry(edit_win, width=15)
        due_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        due_date_entry.insert(0, task[2] if task[2] else "")
        
        # Priority
        tk.Label(edit_win, text="Priority:").grid(row=2, column=0, sticky='w')
        priority_var = tk.StringVar(value=task[0])
        tk.Radiobutton(edit_win, text="High", variable=priority_var, value="High").grid(row=2, column=1, sticky='w')
        tk.Radiobutton(edit_win, text="Medium", variable=priority_var, value="Medium").grid(row=3, column=1, sticky='w')
        tk.Radiobutton(edit_win, text="Low", variable=priority_var, value="Low").grid(row=4, column=1, sticky='w')
        
        # Category
        tk.Label(edit_win, text="Category:").grid(row=5, column=0, sticky='w')
        categories = ["General", "Work", "Personal", "Health", "Finance", "Learning"]
        category_var = tk.StringVar(value=task[3])
        category_menu = tk.OptionMenu(edit_win, category_var, *categories)
        category_menu.grid(row=5, column=1, sticky='w', padx=5)
        
        # Time estimate
        tk.Label(edit_win, text="Time Estimate (minutes):").grid(row=6, column=0, sticky='w')
        time_entry = tk.Entry(edit_win, width=10)
        time_entry.grid(row=6, column=1, sticky='w', padx=5)
        time_entry.insert(0, str(task[4]))
        
        # Save button
        def save_changes():
            self.cursor.execute('''
                UPDATE tasks SET
                    priority = ?,
                    task = ?,
                    due_date = ?,
                    category = ?,
                    time_estimate = ?
                WHERE id = ?
            ''', (
                priority_var.get(),
                task_entry.get(),
                due_date_entry.get() if due_date_entry.get() else None,
                category_var.get(),
                int(time_entry.get()),
                task_id
            ))
            self.conn.commit()
            self.refresh_task_list()
            edit_win.destroy()
        
        tk.Button(edit_win, text="Save Changes", command=save_changes).grid(row=7, column=0, columnspan=2, pady=10)
    
    def sort_tasks(self, column):
        # Determine sort order
        if column == "Priority":
            order_by = '''
                CASE priority 
                    WHEN 'High' THEN 1 
                    WHEN 'Medium' THEN 2 
                    WHEN 'Low' THEN 3 
                    ELSE 4 
                END
            '''
        elif column == "Due Date":
            order_by = "due_date IS NULL, due_date"
        elif column == "Days Left":
            order_by = '''
                CASE 
                    WHEN due_date IS NULL THEN 1
                    ELSE julianday(due_date) - julianday('now')
                END
            '''
        elif column == "Time Estimate":
            order_by = "time_estimate"
        else:
            order_by = column.lower().replace(" ", "_")
        
        # Get sorted tasks from database
        self.cursor.execute(f'''
            SELECT id, priority, task, due_date, category, time_estimate 
            FROM tasks 
            WHERE user_id=? AND completed=0
            ORDER BY {order_by}
        ''', (self.current_user["id"],))
        tasks = self.cursor.fetchall()
        
        # Update task tree
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        today = datetime.now().date()
        
        for task in tasks:
            task_id = task[0]
            priority = task[1]
            task_text = task[2]
            due_date = task[3]
            category = task[4]
            time_estimate = task[5]
            
            tags = ()
            if priority == "High":
                tags = ('high',)
            elif priority == "Low":
                tags = ('low',)
            
            # Calculate days left
            days_left = ""
            if due_date:
                try:
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                    delta = (due_date_obj - today).days
                    days_left = str(delta)
                    if delta < 0:
                        tags += ('overdue',)
                    elif delta == 0:
                        tags += ('due-today',)
                    elif delta <= 3:
                        tags += ('due-soon',)
                except:
                    pass
            
            self.task_tree.insert("", tk.END, iid=task_id, values=(
                priority,
                task_text,
                due_date if due_date else "",
                days_left,
                category,
                f"{time_estimate} min"
            ), tags=tags)
    
    def generate_ai_suggestions(self):
        """Generate AI-based task suggestions"""
        current_date = datetime.now()
        suggestions = [
            ("Review project documentation", f"{(current_date + timedelta(days=2)).strftime('%Y-%m-%d')}", "Work", 60),
            ("Call dentist to schedule checkup", f"{(current_date + timedelta(days=14)).strftime('%Y-%m-%d')}", "Health", 30),
            ("Pay electricity bill - urgent", current_date.strftime('%Y-%m-%d'), "Finance", 15),
            ("Prepare presentation for client meeting", f"{(current_date + timedelta(days=7)).strftime('%Y-%m-%d')}", "Work", 120),
            ("30 minutes of exercise", "", "Health", 30),
            ("Read new research paper about AI", "", "Learning", 60),
            ("Plan weekend family outing", f"{(current_date + timedelta(days=(5 - current_date.weekday()) % 7)).strftime('%Y-%m-%d')}", "Personal", 90)
        ]
        
        selected_suggestion = random.choice(suggestions)
        self.task_entry.delete(0, tk.END)
        self.task_entry.insert(0, selected_suggestion[0])
        
        self.due_date_var.set(selected_suggestion[1])
    
    def smart_schedule(self):
        """Fixed version that properly distributes tasks across days"""
        self.cursor.execute('''
            SELECT task, priority, due_date, time_estimate 
            FROM tasks 
            WHERE user_id=? AND completed=0
            ORDER BY 
                CASE priority 
                    WHEN 'High' THEN 1 
                    WHEN 'Medium' THEN 2 
                    WHEN 'Low' THEN 3 
                    ELSE 4 
                END,
                due_date IS NULL,
                due_date
        ''', (self.current_user["id"],))
        tasks = self.cursor.fetchall()
        
        if not tasks:
            messagebox.showinfo("Info", "No tasks to schedule")
            return
        
        schedule = []
        current_date = datetime.now().date()
        available_minutes = 240  # 4 hours per day
        
        for task in tasks:
            task_text, priority, due_date_str, time_estimate = task
            time_estimate = int(time_estimate)
            
            # Parse due date (if exists)
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date() if due_date_str else None
            
            # Find the best day to schedule
            schedule_date = current_date
            while True:
                # Case 1: Task fits in current day
                if available_minutes >= time_estimate:
                    available_minutes -= time_estimate
                    break
                
                # Case 2: Move to next day
                schedule_date += timedelta(days=1)
                available_minutes = 240  # Reset for new day
                
                # Stop if we're past due date (for tasks with deadlines)
                if due_date and schedule_date > due_date:
                    schedule_date = due_date
                    break
            
            # Format schedule day
            if schedule_date == current_date:
                schedule_day = "Today"
            elif schedule_date == current_date + timedelta(days=1):
                schedule_day = "Tomorrow"
            else:
                schedule_day = schedule_date.strftime("%A, %b %d")
            
            schedule.append(f"{task_text} ({priority} priority, {time_estimate} min)")
        
        # Show the schedule
        schedule_text = "Smart Schedule:\n\n" + "\n".join(schedule)
        messagebox.showinfo("Smart Schedule", schedule_text)

if __name__ == "__main__":
    app = TodoApp()
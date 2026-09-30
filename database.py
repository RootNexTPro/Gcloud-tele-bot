import sqlite3
import os
import datetime

DB_FILE = 'bot_database.db'

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            credits INTEGER DEFAULT 0,
            daily_quota_used INTEGER DEFAULT 0,
            last_quota_reset DATE,
            referred_by INTEGER,
            joined_at DATETIME
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            added_by INTEGER,
            added_at DATETIME
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_user_id INTEGER UNIQUE,
            reward_granted INTEGER DEFAULT 2,
            created_at DATETIME
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS deployments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            mode TEXT,
            gcp_project_id TEXT,
            cloudrun_url TEXT,
            cost_credits INTEGER,
            created_at DATETIME
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS credit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            reason TEXT,
            timestamp DATETIME
        )
    ''')

    # Initialize super admin
    admin_id_str = os.environ.get('INITIAL_ADMIN_ID')
    if admin_id_str:
        try:
            admin_id = int(admin_id_str)
            c.execute('INSERT OR IGNORE INTO admins (user_id, added_at) VALUES (?, ?)',
                      (admin_id, datetime.datetime.now()))
        except ValueError:
            pass

    conn.commit()
    conn.close()

def add_user(user_id, username, first_name, referred_by=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not c.fetchone():
        c.execute('''
            INSERT INTO users (user_id, username, first_name, last_quota_reset, referred_by, joined_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, datetime.date.today(), referred_by, datetime.datetime.now()))

        if referred_by:
            # Handle referral reward
            c.execute('SELECT * FROM users WHERE user_id = ?', (referred_by,))
            if c.fetchone():
                c.execute('INSERT INTO referrals (referrer_id, referred_user_id, created_at) VALUES (?, ?, ?)',
                          (referred_by, user_id, datetime.datetime.now()))
                # Add 2 credits to referrer
                c.execute('UPDATE users SET credits = credits + ? WHERE user_id = ?', (2, referred_by))
                c.execute('INSERT INTO credit_logs (user_id, amount, reason, timestamp) VALUES (?, ?, ?, ?)',
                          (referred_by, 2, f"Referral reward for user {user_id}", datetime.datetime.now()))
                # Add 1 credit to referred user
                c.execute('UPDATE users SET credits = credits + ? WHERE user_id = ?', (1, user_id))
                c.execute('INSERT INTO credit_logs (user_id, amount, reason, timestamp) VALUES (?, ?, ?, ?)',
                          (user_id, 1, f"Referred by user {referred_by}", datetime.datetime.now()))

        conn.commit()
    conn.close()

def is_admin(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM admins WHERE user_id = ?', (user_id,))
    admin = c.fetchone()
    conn.close()
    return bool(admin)

def add_admin(user_id, added_by):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?, ?, ?)',
              (user_id, added_by, datetime.datetime.now()))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def list_admins():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT user_id FROM admins')
    admins = [row[0] for row in c.fetchall()]
    conn.close()
    return admins

def list_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def adjust_credits(user_id, amount, reason):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET credits = credits + ? WHERE user_id = ?', (amount, user_id))
    c.execute('INSERT INTO credit_logs (user_id, amount, reason, timestamp) VALUES (?, ?, ?, ?)',
              (user_id, amount, reason, datetime.datetime.now()))
    conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT credits, daily_quota_used, last_quota_reset FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    if not user:
        return None
    return {
        'credits': user[0],
        'daily_quota_used': user[1],
        'last_quota_reset': user[2]
    }

def check_and_use_quota_or_credit(user_id):
    if is_admin(user_id):
        return True, "Admin unlimited deployments."

    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT credits, daily_quota_used, last_quota_reset FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()

    if not user:
        conn.close()
        return False, "User not found."

    credits = user[0]
    daily_quota_used = user[1]
    last_quota_reset = datetime.datetime.strptime(user[2], "%Y-%m-%d").date() if isinstance(user[2], str) else user[2]
    today = datetime.date.today()

    if last_quota_reset != today:
        daily_quota_used = 0
        c.execute('UPDATE users SET daily_quota_used = 0, last_quota_reset = ? WHERE user_id = ?', (today, user_id))

    if daily_quota_used < 1:
        c.execute('UPDATE users SET daily_quota_used = daily_quota_used + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        return True, "Used daily free quota."
    elif credits > 0:
        conn.close()
        adjust_credits(user_id, -1, "Deployment cost")
        return True, "Used 1 credit."
    else:
        conn.close()
        return False, "Not enough credits and daily quota exceeded."

def refund_credit(user_id):
    if not is_admin(user_id):
        adjust_credits(user_id, 1, "Deployment failed refund")

def log_deployment(user_id, mode, project_id, cloudrun_url, cost):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO deployments (user_id, mode, gcp_project_id, cloudrun_url, cost_credits, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, mode, project_id, cloudrun_url, cost, datetime.datetime.now()))
    conn.commit()
    conn.close()

def get_referral_stats(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_global_stats():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM deployments')
    total_deployments = c.fetchone()[0]
    conn.close()
    return total_users, total_deployments

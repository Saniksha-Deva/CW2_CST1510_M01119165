import sqlite3

def add_user(conn, name, hash):
    cur = conn.cursor()
    sql = '''INSERT INTO users (username, password_hash) VALUES (?, ?) '''
    param = (name, hash)
    cur.execute(sql, param)
    conn.commit()


def migrate_users(conn):
    with open('DATA/users.txt', 'r') as f:
        users = f.readlines()

    for user in users:
        name, hash = user.strip().split(',')
        add_user(conn, name, hash)

# read data from user
def get_all_users(conn):
    cur = conn.cursor()
    sql = '''SELECT * FROM users '''
    cur.execute(sql)
    users = cur.fetchall()
    #conn.close()
    return(users)

# Get one user by username
def get_user(conn, name):
    cur = conn.cursor()
    sql = '''SELECT * FROM users WHERE username = ? '''
    param = (name,)
    cur.execute(sql, param)
    user = cur.fetchone()
    #conn.close()
    return(user)

# UPDATE - change a username
def update_user(conn, old_name, new_name):
    cur = conn.cursor()
    sql = 'UPDATE users SET username = ? WHERE username = ?'
    param = (new_name, old_name)
    cur.execute(sql, param)
    conn.commit()

# DELETE - remove a user
def delete_user(conn, user_name):
    cur = conn.cursor()
    sql = 'DELETE FROM users WHERE username = ?'
    param = (user_name,)
    cur.execute(sql, param)
    conn.commit()

# Adding admin role
def update_user_role(conn, username, new_role):
    cur = conn.cursor()
    sql = 'UPDATE users SET role = ? WHERE username = ?'
    param = (new_role, username)
    cur.execute(sql, param)
    conn.commit()

# Search user by name
def search_user(conn, search_term):
    cur = conn.cursor()
    sql = 'SELECT * FROM users WHERE username LIKE ?'
    param = ('%' + search_term + '%',)
    cur.execute(sql, param)
    users = cur.fetchall()
    return(users)

# Adding column for totp secrets
def totp_column(conn):
    cur = conn.cursor()
    try:
        sql = 'ALTER TABLE users ADD COLUMN totp_secret TEXT DEFAULT NULL'
        cur.execute(sql)
        conn.commit()
    except sqlite3.OperationalError as e:
        # Do not do anything since the column already exists
        pass

def create_user(conn, name, hash, totp_secret, role="user"):
    cur = conn.cursor()
    sql = 'INSERT INTO users (username, password_hash, role, totp_secret) VALUES (?, ?, ?, ?)'
    param = (name, hash, role, totp_secret)
    cur.execute(sql, param)
    conn.commit()

# Assign totp_secret to users with Null totp_secret
def set_totp_secret(conn, username, secret):
    cur = conn.cursor()
    sql = 'UPDATE users SET totp_secret = ? WHERE username = ?'
    param = (secret, username)
    cur.execute(sql, param)
    conn.commit()

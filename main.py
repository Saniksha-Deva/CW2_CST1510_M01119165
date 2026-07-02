import sqlite3
import pandas as pd

from app_model.db import get_connection
from app_model.users import add_user, get_user, update_user_role
from hashing import generate_hash, is_valid_hash

conn = get_connection()

# User registration
def register_user(conn):
    name = input('Enter your name: > ')
    password = input('Enter your password: > ')
    hash_password = generate_hash(password)
    add_user(conn, name, hash_password)


# User log in
def login_user(conn):
    name = input('Enter your name: > ')
    password = input('Enter your password: > ')
    id, user_name, user_hash, *_ = get_user(conn, name)
    print(f'Welcome {user_name}!!')
    if name == user_name and is_valid_hash(password, user_hash):
            return True
    return False

def main():
    while True:
        print('1. To Register\n2. To Log in\n3. To Exit')
        choice = input(': > ')
        if choice == '1':
            register_user(conn)
        elif choice == '2':
            print('Login successful!' if login_user(conn) else 
'Incorrect login.')
        elif choice == '3':
            print('Goodbye!'); break

# Update user to admin
#update_user_role(conn, 'Admin', 'admin')

if __name__ =='__main__':
    main()


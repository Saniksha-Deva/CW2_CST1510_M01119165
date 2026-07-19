# Multi-Domain Intelligence Platform

## Requirements
- Install dependencies: pip install -r requirements.txt

## Setup
Create a .streamlit folder and then create a file called 'secrets.toml'
This is where the api key secret key will be manually added
The file should have the line:
GROQ_API_KEY = "YOUR_API_"KEY"

## Running the application
Run: streamlit run main.py

## Accessing admin role:
There are two admins with NULL totp_secrets
These admins can be used to login as an admin
Admin details:
Username: Saniksha 
Password: saniksha123

Username: Adam
Password: adam4

When logging in with these admins the totp will have to be enabled by clicking login then scanning the QR code and entering the 2FA code then clicking login again

## GitHub

Repository:
https://github.com/Saniksha-Deva/CW2_CST1510_M01119165

Clone using:
git clone https://github.com/Saniksha-Deva/CW2_CST1510_M01119165.git

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

#if __name__ =='__main__':
#    main()

import streamlit as st
from hashing import generate_hash, is_valid_hash
from app_model.db import get_connection
from app_model.users import add_user, get_user, get_all_users, search_user, update_user, delete_user, update_user_role
from app_model.cyber_incidents import get_all_cyber_incidents
from app_model.metadatas import get_all_datasets_metadata
from app_model.it_tickets import get_all_it_tickets
import pandas as pd
import plotly.express as px
import time 
from groq import Groq
from PIL import Image
import bcrypt


conn = get_connection()

# ---------- PAGES ----------

def home_page():
   """Page that shows what the platform is about and allows a user to login/register"""
   st.set_page_config(
        page_title="Home",
        page_icon="🏠",
        layout="wide"
    )

   st.title("Welcome to the Multi-Domain Intelligence Platform")
   st.subheader("This platform splits into three separate dashboards to monitor cyber incidents, IT issues and keep track of the datasets.")

    # ---------- Initialise session state ----------
    # Make sure 'logged_in' exists in session state
   if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
       
    # Redirect to the register page
   if st.button("Get Started"):
       st.switch_page(register)
       

def login_page():
    """Creates a page where the user can login from"""
    st.set_page_config(
        page_title="Login",
        page_icon="🔒",
        layout="wide"
    )

    st.title("Login 🔒")

    with st.form("login_form"):
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Login")

    if submitted:
        # Check that fields are not empty
        if not login_username.strip() or not login_password.strip():
            st.error("Enter both a username and password.")
            return
        
        if not login_limit(login_username, action="check"):
            return

        # Get the user record from the database
        user = get_user(conn, login_username)

        if user is None:
            login_limit(login_username, action="update", login_success=False)
            st.error("Incorrect username or password")
            return 
        
        id, user_name, user_hash, *_ = user

        # Verify the password against the stored hash
        if login_username and is_valid_hash(login_password, user_hash):
            login_limit(login_username, action="update", login_success=True)
            st.session_state.logged_in = True
            st.session_state.username = user_name
            st.success("Logged in successfully!")
            # Redirect the user to the dashboard after logging in
            st.switch_page(cyber)
        else:
            login_limit(login_username, action="update", login_success=False)
            st.error("Incorrect username or password")



def register_page():
    """Creates a page for new users to create an account"""
    st.set_page_config(
        page_title="Register",
        page_icon="📝",
        layout="wide"
    )

    st.title("Create Account 📝")

    with st.form("register_form"):
        register_username = st.text_input("New Username")
        register_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        hash_password = generate_hash(register_password)
        submitted = st.form_submit_button("Register")

        if submitted:
            # Validate imputs
            if not register_username or not register_password:
                st.error("All fields are required.")
                return
            
            if register_password != confirm_password:
                st.error("Passwords do not match.")
                return
            
            if len(register_password) < 8:
                st.error("Passwords must be at least 8 characters.")
                return
            
            if len(register_password) > 12:
                st.error("Password cannot be more than 12 characters.")
                return
            
            if " " in register_password:
                st.error("Password cannot have blank spaces.")
                return
            
            # Attempt to add the user to the database
            try:
                add_user(conn, register_username, hash_password)
                st.success("Account created! Please log in.")
                st.switch_page(home_page)
            except Exception as e:
                st.error("Username already exists.")
            finally:
                conn.close()
        st.divider()
        st.write("Already have an account?")
        # Go to the login page 
        if st.form_submit_button("Login"):
            st.switch_page(login)


def cyber_incidents_dashboard():
    """Displays information regarding cyber incidents"""
    st.set_page_config(
        page_title="Cyber Incidents Dashboard",
        page_icon="🛡️",
        layout="wide"
    )

    # Make sure 'logged_in' exists in session state
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # Deny access to unauthorized users
    if not st.session_state['logged_in']:
        st.warning("Please log in to access the dashboard.")
        if st.button("Go to Login Page"):
            st.session_state['logged_in'] = False
            st.switch_page(st.session_state.login)
        st.stop()
    else:
        st.success("You are logged in!")

    # Get all cyber incident records from the database
    cyber_data = get_all_cyber_incidents(conn)

    st.title("Welcome to the Cyber Incidents Dashboard")

    cyber_data['timestamp'] = pd.to_datetime(cyber_data['timestamp'])

    # Allow the user to choose a specific severity level to focus on
    with st.sidebar:
        st.header("Navigation")
        severity_ = st.selectbox('Severity Level', cyber_data['severity'].unique())
        status_ = st.selectbox('Status', cyber_data['status'].unique())
    filtered_data = cyber_data[cyber_data['severity'] == severity_]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"Cyber Incidents with Severity: {severity_}")
        st.bar_chart(filtered_data['category'].value_counts())

    with col2:
        st.subheader("Category Trend Over Time")
        st.line_chart(filtered_data, x= 'timestamp', y= 'category')

    col3, col4 = st.columns(2)

    with col3:
        st.subheader(f"Severity for {severity_} at certain times")
        st.bar_chart(filtered_data['timestamp'].dt.hour.value_counts(), x_label="Hour of Day", y_label="Number of Incidents")

    with col4:
        st.subheader("Filtered Data")
        st.dataframe(filtered_data)

    # Pie chart showing total cyber incidents for each of the severity levels
    severity_level = cyber_data['severity'].value_counts()
    severity_chart = px.pie(values=severity_level, names=severity_level.index, title="Total Cyber Incidents for each Severity level")
    st.plotly_chart(severity_chart)

    # Bar chart showing total cyber incidents for each category and filtered by status
    filtered_status = cyber_data[cyber_data['status'] == status_]
    st.subheader(f"Cyber Incidents with Status: {status_}")
    st.bar_chart(filtered_status['category'].value_counts())

    ai_analyser(domain="Cybersecurity")

    # Logs out a user and redirects them to the home page
    st.divider()
    if st.button("Log out"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.info("You have been logged out.")
        st.switch_page(st.session_state.home)

def datasets_dashboard():
    """Displays information about the data"""
    st.set_page_config(
        page_title="Datasets Metadata Dashboard",
        page_icon="📊",
        layout="wide"
    )

    # Deny access to unauthorized users
    if not st.session_state['logged_in']:
        st.warning("Please log in to access the dashboard.")
        if st.button("Go to Login Page"):
            st.session_state['logged_in'] = False
            st.switch_page(st.session_state.login)
        st.stop()
    else:
        st.success("You are logged in!")

    # Get all metadata records from the database 
    datasets_data = get_all_datasets_metadata(conn)

    st.title("Welcome to the Datasets Metadata Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        # Line chart showing datset uploads over time
        st.subheader("Datasets uploaded over time")
        st.line_chart(datasets_data, x= 'upload_date', y= 'name')

    with col2:
        # Pie chart showing the total datasets uploaded by each role
        st.subheader("Uploaded Data")
        upload_data = datasets_data['uploaded_by'].value_counts()
        upload_chart = px.pie(values=upload_data, names=upload_data.index)
        st.plotly_chart(upload_chart)

    # Horizontal bar chart to compare the sizes of the datsets
    st.subheader("Size of Datasets")
    st.bar_chart(datasets_data, x='name', y='rows', horizontal=True, sort="rows")

    ai_analyser(domain="Data Science")

def it_tickets_dashboard():
    """Displays information about the IT tickets"""
    st.set_page_config(
        page_title="IT Tickets Dashboard",
        page_icon="🎫",
        layout="wide"
    )

    # Deny access to unauthorized users
    if not st.session_state['logged_in']:
        st.warning("Please log in to access the dashboard.")
        if st.button("Go to Login Page"):
            st.session_state['logged_in'] = False
            st.switch_page(st.session_state.login)
        st.stop()
    else:
        st.success("You are logged in!")

    # Get all IT ticket records from the database
    it_data = get_all_it_tickets(conn)

    st.title("Welcome to the IT Tickets Dashboard")

    # Allow the user to choose a specific priority to focus on
    with st.sidebar:
        st.header("Navigation")
        priority_ = st.selectbox('priority', it_data['priority'].unique())
    filtered_data = it_data[it_data['priority'] == priority_]

    # Bar chart showing count of status for selected priority
    st.subheader(f"Status for Priority: {priority_}")
    st.bar_chart(filtered_data['status'].value_counts())

    # Pie chart showing count of tickets assigned to IT support filtered by priority
    st.subheader(f"Tickets with priority {priority_} and total assigned for each IT support")
    assigned_data = filtered_data['assigned_to'].value_counts()
    assigned_chart = px.pie(values=assigned_data, names=assigned_data.index)
    st.plotly_chart(assigned_chart)

    # Bar chart showing resolution time for each ticket filtered by priority
    st.subheader("Resolution Time")
    st.bar_chart(filtered_data, x='ticket_id', y='resolution_time_hours')

    it_data['created_at'] = pd.to_datetime(it_data['created_at'])
    # Line chart showing count of tickets created over time
    st.subheader("Tickets created over time")
    # Group tickets by month name and count how many were created in each month
    ticket_counts = (it_data.groupby(it_data['created_at'].dt.strftime('%b'))['ticket_id'].count().reset_index(name='Ticket Count'))
    # Sort the months in order using pd.Categorial instead of using alphabetical order
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    ticket_counts['created_at'] = pd.Categorical(ticket_counts['created_at'], categories=month_order, ordered=True)
    ticket_counts = ticket_counts.sort_values('created_at')
    st.line_chart(ticket_counts, x='created_at', y='Ticket Count', x_label='Month', y_label="Number of Tickets")

    ai_analyser(domain="IT Operations")
    
# ---------- Admin Dashboard and Features ----------

def manage_users(conn):
    
    st.subheader("Registered Users")
    with st.container(border=True):
        search_term = st.text_input("Search", placeholder="Search by Name", label_visibility="collapsed")
        if search_term:
            names = search_user(conn, search_term)
        else:
            names = get_all_users(conn)

        if names:
            df = pd.DataFrame(names, columns=["id", "username", "password_hash", "role"])

            # Display table headers manually
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            col1.write("ID")
            col2.write("Name")
            col3.write("Role")
            col4.write("Edit")
            col5.write("Promote User")
            col6.write("Delete")

            for index, row in df.iterrows():
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    col1.write(row['id'])
                    col2.write(row['username'])
                    col3.write(row['role'])
                    
                    # Edit a user
                    with col4.expander("Edit"):
                        new_name = st.text_input("New Name", value=row['username'], key=f"input_{index}")
                        if st.button("Save Changes", key=f"save_{index}"):
                            update_user(conn, row['username'], new_name)
                            st.success("Updated!")
                            st.rerun()
                    
                    # Promote user to admin
                    with col5.popover("Promote"):
                        if row['role'] == 'admin':
                            st.info(f"{row['username']} is already an Admin.")
                            st.warning(f"Change {row['username']} to User?")
                            if st.button("Confirm", key=f"demote_{index}"):
                                update_user_role(conn, row['username'], 'user')
                                st.success("Changed back to regular user!")
                                st.rerun()
                        else:
                            st.warning(f"Promote {row['username']} to Admin role?")
                            if st.button("Confirm Promotion", key=f"promote_{row['username']}_{index}"):
                                # Calls your model's function to change role to 'admin'
                                update_user_role(conn, row['username'], 'admin')
                                st.success("Upgraded to Admin!")
                                st.rerun()

                    # Delete a user 
                    with col6.popover("Delete"):
                        # Confirm deletion before deleting the user
                        st.warning(f"Are you sure you want to delete {row['username']}?")
                        
                        if st.button("Yes, Confirm Delete", key=f"delete_{row['username']}_{index}"):
                            delete_user(conn, row['username'])
                            st.success("Deleted!")
                            st.rerun()


def dashboard_overview():
    cursor = conn.cursor()

    cyber_col, it_col = st.columns(2)

    with cyber_col:
        # Cyber Incidents Metrics
        with st.container(border=True):
            st.subheader("Cyber Incidents 🛡️")
            # Count cyber incidents with status Open
            cursor.execute("SELECT COUNT(*) FROM cyber_incidents WHERE status = 'Open'")
            open_count = cursor.fetchone()[0]

            # Count cyber incidents with status In Progress
            cursor.execute("SELECT COUNT(*) FROM cyber_incidents WHERE status = 'In Progress'")
            progress_count = cursor.fetchone()[0]

            # Count cyber incidents with status Resolved
            cursor.execute("SELECT COUNT(*) FROM cyber_incidents WHERE status = 'Resolved'")
            resolved_count = cursor.fetchone()[0]

            # Count cyber incidents with status Closed
            cursor.execute("SELECT COUNT(*) FROM cyber_incidents WHERE status = 'Closed'")
            closed_count = cursor.fetchone()[0]

            col1, col2, col3, col4 = st.columns(4)

        # Maximum value for progress bar
            max_value = 50

            with col1:
                with st.container(border=True):
                    st.metric(label="Open", value=open_count)
                    st.progress(min(open_count / max_value, 1.0))
            with col2:
                with st.container(border=True):
                    st.metric(label="In Progress", value=progress_count)
                    st.progress(min(progress_count / max_value, 1.0))
            with col3:
                with st.container(border=True):
                    st.metric(label="Resolved", value=resolved_count)
                    st.progress(min(resolved_count / max_value, 1.0))
            with col4:
                with st.container(border=True):
                    st.metric(label="Closed", value=closed_count)
                    st.progress(min(closed_count / max_value, 1.0))

    with it_col:
        # IT tickets Metrics
        with st.container(border=True):
            st.subheader("IT Tickets 🎫")
            # Count IT tickets with status Open
            cursor.execute("SELECT COUNT(*) FROM it_tickets WHERE status = 'Open'")
            open_count = cursor.fetchone()[0]

            # Count IT tickets with status In Progress
            cursor.execute("SELECT COUNT(*) FROM it_tickets WHERE status = 'In Progress'")
            progress_count = cursor.fetchone()[0]

            # Count IT tickets with status Waiting for User
            cursor.execute("SELECT COUNT(*) FROM it_tickets WHERE status = 'Waiting for User'")
            waiting_count = cursor.fetchone()[0]

            # Count IT tickets with status Resolved
            cursor.execute("SELECT COUNT(*) FROM it_tickets WHERE status = 'Resolved'")
            resolved_count = cursor.fetchone()[0]

            col1, col2, col3, col4 = st.columns(4)

            # Maximum value for progress bar
            max_value = 100

            with col1:
                with st.container(border=True):
                    st.metric(label="Open", value=open_count)
                    st.progress(min(open_count / max_value, 1.0))
            with col2:
                with st.container(border=True):
                    st.metric(label="In Progress", value=progress_count)
                    st.progress(min(progress_count / max_value, 1.0))
            with col3:
                with st.container(border=True):
                    st.metric(label="Waiting for User", value=waiting_count)
                    st.progress(min(waiting_count / max_value, 1.0))
            with col4:
                with st.container(border=True):
                    st.metric(label="Resolved", value=resolved_count)
                    st.progress(min(resolved_count / max_value, 1.0))

    with st.container(border=True):
         # Count total users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
       
        # Count total datasets
        cursor.execute("SELECT COUNT(*) FROM datasets_metadata")
        dataset_count = cursor.fetchone()[0]
        
        col1, col2 = st.columns(2)

        with col1:
            st.metric(label="Total Users👤", value=user_count)
        with col2:
            st.metric(label="Total Datasets 📊", value=dataset_count)


def admin_dashboard():
    st.set_page_config(
        page_title="Admin Dashboard",
        layout="wide"
    )

    current_user = st.session_state.get('username')

    if not current_user:
        st.error("Please log in first.")
        st.stop()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT role FROM users WHERE username = ?", (current_user,))
    result = cursor.fetchone()
    

    user_role = result[0] if result else None

    if user_role != 'admin':
        st.warning("This page can only be accessed by admins.")
        st.stop()

    st.title("Welcome to the Admin Dashboard")

    dashboard_overview()
    
    manage_users(conn)
    conn.close()

    unlock_user()

# Track locked users
if "locked_users" not in st.session_state:
    st.session_state.locked_users = {}

def countdown(username, countdown_seconds):
    countdown_placeholder = st.empty()
    for i in range(countdown_seconds, 0, -1):
        if username not in st.session_state.locked_users:
            st.session_state.login_attempt[username] = 0
            countdown_placeholder.success(f"An admin has unlocked your account. You can log in now.")
            st.rerun()

        countdown_placeholder.error(f"Rate limit exceeded. Please wait {i} seconds.")
        time.sleep(1)

    if username in st.session_state.locked_users:
        del st.session_state.locked_users[username]
    
    st.session_state.login_attempt[username] = 0
    #st.session_state.rate_limit_time = 0
    countdown_placeholder.success("You can try logging in now.")

def login_limit(username, action, login_success=None):
    if 'login_attempt' not in st.session_state:
        st.session_state.login_attempt = {}

    attempts = 3
    rate_limit = 300
    current_time = time.time()

    if username in st.session_state.locked_users:
        lockout_end = st.session_state.locked_users[username]
        lockout_time = int(lockout_end - current_time)

        if lockout_time > 0:
            if action == "check":
                countdown(username, lockout_time)
                return False
        else:
            del st.session_state.locked_users[username]
            st.session_state.login_attempt[username] = 0

    if action == "check":
        return True
    
    if action == "update":
        current_attempts = st.session_state.login_attempt.get(username, 0)

        if login_success is False:
            current_attempts += 1
            st.session_state.login_attempt[username] = current_attempts
            remaining_attempts = attempts - current_attempts

            if current_attempts >= attempts:
                st.session_state.locked_users[username] = current_time + rate_limit
                countdown(username, rate_limit)
            else:
                st.warning(f"You have {remaining_attempts} attempts left.")

        elif login_success is True:
            st.session_state.login_attempt[username] = 0
            if username in st.session_state.locked_users:
                del st.session_state.locked_users[username]

def unlock_user():
    st.subheader("Locked Users")
    with st.container():
        if not st.session_state.locked_users:
            st.info("No users are currently locked out.")
            return
        
        for username, lockout_end in list(st.session_state.locked_users.items()):
            remaining = int(lockout_end - time.time())

            if remaining > 0:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{username} - {remaining} seconds remaining")
                with col2:
                    if st.button(f"Unlock {username}", key=f"unlock_{username}"):
                        del st.session_state.locked_users[username]
                        st.session_state.login_attempt[username] = 0
                        st.success(f"Unlocked {username}")
                        st.rerun()

SYSTEM_PROMPTS = {
    "Cybersecurity": """
Act as a senior cybersecurity analyst and incident intelligence specialist.

SCOPE RESTRICTION:
You are strictly limited to the cybersecurity incident data explicitly provided to you in the current input.
You may only answer questions, generate analysis, or make observations that are directly supported by that provided data.
Do not use outside knowledge, general cybersecurity facts, current events, prior context, training knowledge, personal opinions, or assumptions beyond what can be reasonably inferred from the dataset.
If a user asks anything that is not supported by the provided data, respond by stating that the request is outside the available data scope and cannot be answered from the dataset alone.

ALLOWED KNOWLEDGE SOURCES:
- Only the incident data provided in the current prompt/input
- Careful logical inferences that are directly supported by the provided fields and descriptions

DISALLOWED BEHAVIOR:
- Do not answer questions about current events, general cybersecurity knowledge, best practices not grounded in the data, vendor-specific facts, threat actor history, malware background, or external context unless explicitly present in the dataset
- Do not invent facts, CVEs, malware names, threat actors, exploit paths, MITRE ATT&CK mappings, or root causes unless strongly supported by the incident descriptions
- Do not fill gaps with likely-sounding information
- Do not present assumptions as facts

REQUIRED OUT-OF-SCOPE RESPONSE:
If the user asks a question that cannot be answered using the provided dataset, say:
"That cannot be determined from the provided incident data alone."
If helpful, briefly add:
"Please provide additional relevant data if you want a more specific answer."

You will be given cybersecurity incident data in CSV format with fields such as:
- index
- incident_id
- timestamp
- severity
- category
- status
- description

Your task is to analyze the data and generate clear, professional, and technically accurate insights for a mixed audience of end users and admins.

Objectives:
1. Identify key trends in the incident data over time
2. Detect anomalies, unusual spikes, or suspicious patterns
3. Highlight likely threats based on incident categories, severity, timestamps, status, and descriptions
4. Infer possible root causes where reasonable from the available data
5. Explain likely attack vectors in practical cybersecurity terms only when supported by the data
6. Use standard cybersecurity terminology where relevant, including:
   - MITRE ATT&CK tactics/techniques only when they can be reasonably inferred from the provided incident descriptions
   - CVE references only if explicitly supported by the incident descriptions or context in the data
7. Prioritize actionable recommendations based only on risk, severity, frequency, and operational impact visible in the data
8. Provide technical guidance that helps the IT team respond effectively while also making the findings understandable to non-expert users where possible

Instructions:
- Base your analysis only on the data provided
- Distinguish clearly between:
  - direct observations from the data
  - cautious inferences supported by the data
  - unknowns that cannot be determined
- If evidence is insufficient, clearly state assumptions, confidence level, or data limitations
- Pay attention to:
  - recurring incident categories
  - repeated severity patterns
  - unresolved or open incidents
  - incident clusters by time
  - indicators of phishing, malware, unauthorized access, misconfiguration, insider risk, or lateral movement only if suggested by the descriptions
- Prioritize the most important risks first
- If a requested conclusion is unsupported, explicitly say it cannot be determined from the data

Output format:
1. Executive Summary
   - Brief overview of the most important findings

2. Key Trends and Patterns
   - Summarize recurring categories, severity distribution, time-based trends, and status patterns

3. Anomalies and Suspicious Findings
   - Highlight unusual incidents, spikes, or deviations from normal patterns

4. Likely Threats and Attack Vectors
   - Explain probable threat types and how the attacks may have occurred only if supported by the data
   - Reference MITRE ATT&CK tactics/techniques only where appropriate and supported

5. Root Cause Analysis
   - Identify likely root causes or contributing factors based on the available data

6. Prioritized Recommendations
   - Provide actionable next steps ranked by urgency and impact
   - Include both technical actions for IT teams and practical guidance for users where relevant
   - Do not include recommendations requiring external assumptions unless clearly labeled as general follow-up options rather than dataset-derived conclusions

7. Data Gaps / Confidence Notes
   - Mention any limitations in the dataset and where more information is needed for stronger conclusions

Style requirements:
- Use a professional, technical tone
- Keep the response concise but insightful
- Use bullet points where they improve readability
- Present recommendations in a clear, prioritized manner
- Avoid excessive jargon when addressing points relevant to end users
""",

    "Data Science": """
Act as a senior data analyst and data quality advisor.

SCOPE RESTRICTION:
You are strictly limited to the dataset metadata explicitly provided to you in the current input.
You may only answer questions, generate analysis, or make observations that are directly supported by that provided metadata.
Do not use outside knowledge, general data science knowledge beyond generic interpretation of the metadata structure, current events, prior context, training knowledge, personal opinions, or assumptions beyond what can be reasonably inferred from the metadata.
If a user asks anything that is not supported by the provided metadata, respond by stating that the request is outside the available data scope and cannot be answered from the metadata alone.

ALLOWED KNOWLEDGE SOURCES:
- Only the metadata provided in the current prompt/input
- Careful logical inferences directly supported by fields such as dataset size, naming, ownership, and dates

DISALLOWED BEHAVIOR:
- Do not assume actual column meanings, data distributions, business definitions, or dataset content unless explicitly provided
- Do not answer general knowledge questions unrelated to the metadata
- Do not invent data quality problems, statistical properties, or domain context not evidenced by the metadata
- Do not fill gaps with likely-sounding assumptions
- Do not present assumptions as facts

REQUIRED OUT-OF-SCOPE RESPONSE:
If the user asks a question that cannot be answered using the provided metadata, say:
"That cannot be determined from the provided metadata alone."
If helpful, briefly add:
"Please provide the dataset contents or additional metadata for a more specific answer."

You will be given dataset metadata with fields such as:
- index
- dataset_id
- name
- rows
- columns
- uploaded_by
- upload_date

Your task is to analyze the metadata and generate clear, professional, technically sound insights for a mixed audience of users and admins.

Objectives:
1. Summarize what can be inferred about the datasets from the metadata provided
2. Suggest appropriate statistical methods that may be useful for analyzing each dataset or the collection of datasets, only at a metadata-informed level
3. Recommend suitable visualization types based on the likely structure and scale of the data
4. Explain the reasoning behind each statistical and visualization recommendation in clear language
5. Flag possible data quality concerns only where the metadata reasonably suggests risk, including:
   - missing values only if indicated or relevant as a possible inspection point rather than a confirmed fact
   - outliers only as a possible consideration requiring content inspection
   - bias only as a possible concern requiring actual data review
   - inconsistent structure
   - insufficient documentation
   - unusually small or large datasets
6. Identify metadata limitations and clearly distinguish between what is known from the metadata and what would require inspection of the actual dataset contents
7. Recommend concrete next steps for users and admins to improve dataset readiness, quality, and usability

Instructions:
- Base the analysis only on the metadata provided
- Do not assume actual column content beyond what is explicitly available
- Clearly separate:
  - confirmed metadata observations
  - reasonable metadata-based inferences
  - unknowns requiring actual dataset inspection
- If metadata is insufficient for a conclusion, clearly state the limitation
- Where useful, infer likely dataset complexity from the number of rows and columns
- Consider whether the metadata suggests issues related to scale, maintenance, ownership, freshness, or usability
- Make the output understandable to both technical and non-technical readers
- Be practical and specific in recommendations
- If a requested conclusion is unsupported, explicitly say it cannot be determined from the metadata

Output format:
1. Overview
   - Brief summary of what the metadata suggests about the dataset or datasets

2. Metadata-Based Insights
   - Key observations from dataset size, naming, ownership, and upload timing

3. Recommended Statistical Methods
   - List suitable methods
   - Explain why each method may be appropriate
   - Note any assumptions or prerequisites
   - Make clear when recommendations are generic because actual dataset contents are unavailable

4. Recommended Visualizations
   - List suitable chart or dashboard types
   - Explain why each visualization would be useful
   - Make clear when recommendations are tentative due to missing content-level details

5. Potential Data Quality Risks
   - Highlight likely issues such as weak naming conventions, missing ownership context, stale datasets, unusual scale, or inconsistent metadata
   - Clearly distinguish confirmed risks from possible inspection areas

6. Concrete Next Steps
   - Separate recommendations for users and admins where relevant
   - Prioritize the most important actions first

7. Limitations and Assumptions
   - Clearly state what cannot be determined from metadata alone

Style requirements:
- Use a professional, technical tone
- Keep the response clear and structured
- Use bullet points where they improve readability
- Explain reasoning in simple but accurate terms for a mixed audience
- Avoid overclaiming when the metadata does not support strong conclusions
""",

    "IT Operations": """
Act as a senior IT service management analyst and technical support advisor.

SCOPE RESTRICTION:
You are strictly limited to the IT ticket data explicitly provided to you in the current input.
You may only answer questions, generate analysis, or make observations that are directly supported by that provided data.
Do not use outside knowledge, general IT knowledge beyond practical interpretation of the ticket fields, current events, prior context, training knowledge, personal opinions, or assumptions beyond what can be reasonably inferred from the dataset.
If a user asks anything that is not supported by the provided ticket data, respond by stating that the request is outside the available data scope and cannot be answered from the dataset alone.

ALLOWED KNOWLEDGE SOURCES:
- Only the IT ticket data provided in the current prompt/input
- Careful logical inferences directly supported by priority, status, timestamps, assignees, resolution times, and descriptions

DISALLOWED BEHAVIOR:
- Do not answer unrelated general IT questions
- Do not invent root causes, infrastructure details, software versions, hardware specifics, or technical diagnoses unless clearly supported by the ticket data
- Do not fill gaps with likely-sounding details
- Do not present assumptions as facts

REQUIRED OUT-OF-SCOPE RESPONSE:
If the user asks a question that cannot be answered using the provided ticket data, say:
"That cannot be determined from the provided ticket data alone."
If helpful, briefly add:
"Please provide additional ticket details or supporting operational data for a more specific answer."

You will be given IT ticket data with fields such as:
- index
- ticket_id
- priority
- description
- status
- assigned_to
- created_at
- resolution_time_hours

Your task is to analyze the IT ticket data and generate clear, professional, and technically sound insights for a mixed audience of users and admins.

Objectives:
1. Identify high-priority issues based on business impact and urgency
2. Detect patterns that may indicate recurring or systemic IT problems
3. Highlight operational bottlenecks using ticket status, assignment, and resolution time information
4. Suggest systematic troubleshooting steps for the most significant or recurring issues only when supported by ticket evidence
5. Recommend preventive measures to reduce repeat incidents and improve service efficiency based on the patterns visible in the data
6. Distinguish between urgent issues that need immediate action and broader systemic issues that require long-term fixes
7. Make the findings understandable to both technical admins and general users where relevant

Instructions:
- Base the analysis only on the data provided
- Use priority, status, timing, assignment patterns, and ticket descriptions to infer impact and urgency
- Do not invent technical details that are not supported by the ticket data
- Clearly separate:
  - direct observations from the ticket data
  - cautious inferences supported by the data
  - unknowns that cannot be determined
- If the description is vague, clearly state assumptions and confidence level
- Look for:
  - repeated issue types in descriptions
  - long resolution times
  - unresolved or stuck tickets
  - overloaded assignees
  - clusters of similar issues over time
  - signs of underlying infrastructure, access, configuration, software, or hardware problems only if suggested by the descriptions
- Separate observations from recommendations
- Prioritize the most business-critical findings first
- If a requested conclusion is unsupported, explicitly say it cannot be determined from the data

Output format:
1. Executive Summary
   - Brief overview of the most important findings

2. Priority and Business Impact Assessment
   - Identify which tickets or issue categories appear most urgent or disruptive
   - Explain why they are high priority

3. Patterns and Systemic Issues
   - Summarize recurring problems, repeated failure points, or support trends

4. Troubleshooting Guidance
   - Provide structured troubleshooting steps for the key issues identified
   - Make steps practical and actionable
   - Only include troubleshooting guidance that is supported by the ticket descriptions and patterns

5. Preventive Measures
   - Recommend process, technical, or user-focused actions to reduce recurrence
   - Keep recommendations tied to observed patterns in the data

6. Operational Concerns
   - Highlight bottlenecks related to ticket status, assignment, or resolution time

7. Limitations and Assumptions
   - Clearly state what cannot be determined from the available ticket data alone

Style requirements:
- Use a professional, technical tone
- Keep the response clear and structured
- Use bullet points where they improve readability
- Make recommendations practical and prioritized
- Avoid unnecessary jargon when writing points relevant to general users
"""
}

def load_domain_data(domain):
    """Load the relevant dataframe for a given domain."""
   
    if domain == "Cybersecurity":
        df = get_all_cyber_incidents(conn)
    elif domain == "Data Science":
        df = get_all_datasets_metadata(conn)
    elif domain == "IT Operations":
        df = get_all_it_tickets(conn)
    else:
        df = None
    return df

def ai_analyser(domain, show_header: bool = True, show_controls: bool = True):
    # Auth guard
    if not st.session_state.get("logged_in", False):
        st.switch_page(st.session_state.home); st.stop()

    if domain not in SYSTEM_PROMPTS:
        st.error(f"Unknown domain '{domain}'. Must be one of: {list(SYSTEM_PROMPTS.keys())}")
        st.stop()

    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    # state_key used so that each domain uses its own system prompt
    state_key = f"ai_messages_{domain.replace(' ', '_').lower()}"

     # Load the domain's data and turn it into text the AI can read
    df = load_domain_data(domain)
    if df is not None and not df.empty:
        data_context = df.to_csv(index=True)
    else:
        data_context = "No data records available at the moment."

    system_content = f"""{SYSTEM_PROMPTS[domain]}
    You have access to the following {domain} data (CSV format, index = record number):
    {data_context}
    When the user refers to a record, records, or a range (e.g. "record 3", "from 2 to 5", "all critical ones"), use the data above to answer. If the data can't answer the question, say so clearly.
    """

    # Initialise chat
    if state_key not in st.session_state:
        st.session_state[state_key] = [{"role": "system", "content": system_content}]
    
    if show_header:
        st.title(f"{domain} Assistant")

    if show_controls:
        col1, col2 = st.columns([4,1])
        with col1:
            st.metric("Messages", max(0, len(st.session_state[state_key]) - 1))
        with col2:
            if st.button("Clear Chat", key=f"clear_{state_key}"):
                st.session_state[state_key] = [{"role": "system", "content": system_content}]
                st.rerun()

    # Display history
    for msg in st.session_state[state_key]:
        if msg["role"] != "system":
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # New input
    if user_input := st.chat_input("Ask a question...", key=f"input_{state_key}"):
        st.session_state[state_key].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b", messages=st.session_state[state_key], stream=True
            )
            full_reply = ""; placeholder = st.empty()
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta: full_reply += delta; placeholder.write(full_reply + "▌ ")
            placeholder.write(full_reply)
            st.session_state[state_key].append({"role": "assistant", "content": full_reply})


def account_settings():
    st.set_page_config(
        page_title="Account Settings",
        page_icon="⚙️",
        layout="wide"
    )

    st.title("Account Settings")
    st.subheader("Manage your account and profile.")

    with st.container(border=True):
        if "profile_picture" not in st.session_state:
            st.session_state["profile_picture"] = None
        col1, col2 = st.columns([1, 4], vertical_alignment="center")
        with col2:
            st.markdown("### Profile Picture")
            st.write("JPG or PNG")

            uploaded_file = st.file_uploader(
                "Upload Photo",
                type=["jpg", "png"],
                label_visibility="collapsed",
                key="profile_uploader"
            )

            if uploaded_file is not None:
                st.session_state["profile_picture"] = Image.open(uploaded_file).resize((125, 125))

            if st.session_state is not None:
                with col1:
                    st.image(st.session_state["profile_picture"])
                with col2:
                    if st.button("Remove"):
                        st.session_state["profile_picture"] = None
                        if "profile_uploader" in st.session_state:
                            del st.session_state["profile_uploader"]
                        st.rerun()

    with st.container(border=True):
        st.subheader("Update Username")
        with st.expander("Edit"):
            current_username = st.session_state.get('username')
            new_name = st.text_input("New Name", value=current_username, key="update_username")
            if st.button("Save Changes", key="save_username"):
                update_user(conn, current_username, new_name)
                st.session_state['username'] = new_name
                st.success("Updated!")
                st.rerun()

    with st.container(border=True):
        st.subheader("Password Management")
        with st.expander("Change Password"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")

            if st.button("Update Password"):
                if not current_password or not new_password or not confirm_password:
                    st.error("All fields are required")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    cursor = conn.cursor()
                    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (current_username,))
                    result = cursor.fetchone()

                    if result:
                        stored_hash = result[0]

                        if bcrypt.checkpw(current_password.encode('utf-8'), stored_hash.encode('utf-8')):
                            new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                            cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, current_username))
                            conn.commit()

                            st.success("Password updated successfully!")
                            st.rerun()
                        else:
                            st.error("Current password is incorrect.")



# ---------- Configure Pages for navigation ----------

home = st.Page(home_page, title="Home", icon="🏠")
login = st.Page(login_page, title="Login")
register = st.Page(register_page, title="Register")
cyber = st.Page(cyber_incidents_dashboard, title="Cyber Incidents Dashboard")
datasets = st.Page(datasets_dashboard, title="Datasets Metadata Dashboard")
it_dashboard = st.Page(it_tickets_dashboard, title="IT Tickets Dashboard")
admin = st.Page(admin_dashboard, title="Admin Dashboard")
account = st.Page(account_settings, title="Account Settings")

st.session_state.home = home
st.session_state.login = login
st.session_state.register = register

# Make sure 'logged_in' exists in session state
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ---------- Page Navigation ----------

pages = [home, login, register, cyber, datasets, it_dashboard, admin, account]
if st.session_state.logged_in:
    # Pages that can be accessed after a user is logged in
    pages = [cyber, datasets, it_dashboard, admin, account]

    with st.sidebar:
        if st.button("Log out"):
            for key in ['logged_in', 'username']:
                del st.session_state[key]
            st.switch_page(st.session_state.home)
            pages = [home, login, register]
else:
    # Pages accessible by logged out users
    pages = [home, login, register]

pg = st.navigation(pages, position="top")
pg.run()
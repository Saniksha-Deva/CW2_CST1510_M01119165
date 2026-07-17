import streamlit as st
from hashing import generate_hash, is_valid_hash
from app_model.db import get_connection
from app_model.users import add_user, get_user, get_all_users, search_user, update_user, delete_user, update_user_role, create_user, totp_column, set_totp_secret
from hashing import generate_hash, is_valid_hash
from app_model.cyber_incidents import get_all_cyber_incidents
from app_model.metadatas import get_all_datasets_metadata
from app_model.it_tickets import get_all_it_tickets
import pandas as pd
import plotly.express as px
import time 
from groq import Groq
from PIL import Image
import bcrypt
import pyotp
import qrcode
import io
from io import BytesIO
from streamlit_extras.dataframe_explorer import *
from PIL import Image, ImageDraw
import groq


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

# Inserting totp_secret column
totp_column(conn)


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
        # Request the second factor (6-digit code)
        totp_code = st.text_input("2FA Code", max_chars=6)
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
        
        id, user_name, user_hash, role, totp_secret = user

        # Verify the password against the stored hash
        if login_username and is_valid_hash(login_password, user_hash):

            if totp_secret is None:
                st.warning("2FA setup required. Scan this QR code, then enter the code and log in again.")

                if "pending_secret" not in st.session_state:
                    st.session_state["pending_secret"] = pyotp.random_base32()

                new_secret = st.session_state["pending_secret"]
                uri = pyotp.TOTP(new_secret).provisioning_uri(name=login_username, issuer_name="MySecureApp")
                qr = qrcode.make(uri)
                buf = io.BytesIO()
                qr.save(buf, format="PNG")
                st.image(buf.getvalue(), caption="Scan this QR code with Google Authenticator or Authy")
                st.write("Manual key: ", new_secret)

                if totp_code.strip() and pyotp.TOTP(new_secret).verify(totp_code):
                    set_totp_secret(conn, login_username, new_secret)
                    del st.session_state["pending_secret"]
                    st.success("2FA enabled. Please log in again.")
                return
                

            totp = pyotp.TOTP(totp_secret)
            # Verify 2FA code
            if totp.verify(totp_code):
                login_limit(login_username, action="update", login_success=True)
                st.session_state.logged_in = True
                st.session_state.username = user_name
                st.session_state.role = role
                st.success("Logged in successfully!")
                # Redirect the user to the dashboard after logging in
                st.switch_page(cyber)
            else:
                login_limit(login_username, action="update", login_success=False)
                st.error("Invalid 2FA code")
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
                totp_secret = pyotp.random_base32()
                create_user(conn, register_username, hash_password, totp_secret)
                st.success("Account created! Please log in.")

                # Generate provisioning URI for the QR code
                totp = pyotp.TOTP(totp_secret)
                uri = totp.provisioning_uri(name=register_username, issuer_name="MySecureApp")

                # Display the QR code for the authenticator app
                qr = qrcode.make(uri)
                buf = io.BytesIO()
                qr.save(buf, format="PNG")

                col_qr, col_txt = st.columns([1, 1.2])
                with col_qr:
                    # Display the QR code image generated in memory
                    st.image(buf.getvalue(), caption="Scan this QR code with Google Authenticator or Authy", use_container_width=True)
                with col_txt:
                    # Provide the manual secret key in case the user cannot scan the QR code
                    st.markdown("**Manual Configuration**")
                    st.caption("If you cannot scan the QR code, use this secret key: ")
                    st.code(totp_secret , language=None)
                    st.warning("Enter this key manually into your Authenticator App")

                st.write("Manual Secret Key (if QR fails): ", totp_secret)

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

    st.title(f"Welcome {st.session_state.username} to the Cyber Incidents Dashboard")

    cyber_data['timestamp'] = pd.to_datetime(cyber_data['timestamp'])

    # Allow the user to choose a specific severity level to focus on
    with st.sidebar:
        st.header("Navigation")
        severity_ = st.selectbox('Severity Level', cyber_data['severity'].unique())
        status_ = st.selectbox('Status', cyber_data['status'].unique())
    filtered_data = cyber_data[cyber_data['severity'] == severity_]

    severity_colors = {
        "Low": "#6FA989",
        "Medium": "#D4B96A",
        "High": "#D68C4A",
        "Critical": "#C1554B"
    }

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"Cyber Incidents with Severity: {severity_}")
        st.bar_chart(filtered_data['category'].value_counts(), height=350, color=severity_colors.get(severity_))

    with col2:
        st.subheader("Category Trend Over Time")
        st.line_chart(filtered_data, x= 'timestamp', y= 'category', height=350, color=severity_colors.get(severity_))

    col3, col4 = st.columns(2)

    with col3:
        st.subheader(f"Severity for {severity_} at certain times")
        st.bar_chart(filtered_data['timestamp'].dt.hour.value_counts(), x_label="Hour of Day", y_label="Number of Incidents", color=severity_colors.get(severity_))

    with col4:
        st.subheader("Filtered Data")
        st.dataframe(filtered_data)

    # Pie chart showing total cyber incidents for each of the severity levels
    severity_level = cyber_data['severity'].value_counts()
    severity_chart = px.pie(values=severity_level, names=severity_level.index, title="Total Cyber Incidents for each Severity level",
                            color=severity_level.index, color_discrete_map=severity_colors)
    st.plotly_chart(severity_chart)

    # Bar chart showing total cyber incidents for each category and filtered by status
    filtered_status = cyber_data[cyber_data['status'] == status_]
    st.subheader(f"Cyber Incidents with Status: {status_}")
    st.bar_chart(filtered_status['category'].value_counts(), color="#3A7CA5")

    ai_analyser(domain="Cybersecurity")


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

    st.title(f"Welcome {st.session_state.username} to the Datasets Metadata Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        # Line chart showing datset uploads over time
        st.subheader("Datasets uploaded over time")
        st.line_chart(datasets_data, x= 'upload_date', y= 'name', height=300, color="#3A7CA5")

    with col2:
        # Pie chart showing the total datasets uploaded by each role
        st.subheader("Uploaded Data")
        upload_data = datasets_data['uploaded_by'].value_counts()
        upload_chart = px.pie(values=upload_data, names=upload_data.index, height=300)
        st.plotly_chart(upload_chart)

    # Horizontal bar chart to compare the sizes of the datsets
    st.subheader("Size of Datasets")
    st.bar_chart(datasets_data, x='name', y='rows', horizontal=True, sort="rows", color="#3A7CA5")

    # Datasets table
    dataframe = datasets_data
    filtered_df = dataframe_explorer(dataframe, case=False)
    st.dataframe(filtered_df, width="stretch")

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

    st.title(f"Welcome {st.session_state.username} to the IT Tickets Dashboard")

    # Allow the user to choose a specific priority to focus on
    with st.sidebar:
        st.header("Navigation")
        priority_ = st.selectbox('priority', it_data['priority'].unique())
    filtered_data = it_data[it_data['priority'] == priority_]

    priority_colors = {
        "Low": "#6FA989",
        "Medium": "#D4B96A",
        "High": "#D68C4A",
        "Critical": "#C1554B"
    }

    # Bar chart showing count of status for selected priority
    st.subheader(f"Status for Priority: {priority_}")
    st.bar_chart(filtered_data['status'].value_counts(), color=priority_colors.get(priority_))

    # Pie chart showing count of tickets assigned to IT support filtered by priority
    st.subheader(f"Tickets with priority {priority_} and total assigned for each IT support")
    assigned_data = filtered_data['assigned_to'].value_counts()
    assigned_chart = px.pie(values=assigned_data, names=assigned_data.index)
    st.plotly_chart(assigned_chart)

    # Bar chart showing resolution time for each ticket filtered by priority
    st.subheader("Resolution Time")
    st.bar_chart(filtered_data, x='ticket_id', y='resolution_time_hours', color=priority_colors.get(priority_))

    it_data['created_at'] = pd.to_datetime(it_data['created_at'])
    # Line chart showing count of tickets created over time
    st.subheader("Tickets created over time")
    # Group tickets by month name and count how many were created in each month
    ticket_counts = (it_data.groupby(it_data['created_at'].dt.strftime('%b'))['ticket_id'].count().reset_index(name='Ticket Count'))
    # Sort the months in order using pd.Categorial instead of using alphabetical order
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    ticket_counts['created_at'] = pd.Categorical(ticket_counts['created_at'], categories=month_order, ordered=True)
    ticket_counts = ticket_counts.sort_values('created_at')
    st.line_chart(ticket_counts, x='created_at', y='Ticket Count', x_label='Month', y_label="Number of Tickets", color="#3A7CA5")

    # IT tickets table
    dataframe = it_data
    filtered_df = dataframe_explorer(dataframe, case=False)
    st.dataframe(filtered_df, width="stretch")

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
            df = pd.DataFrame(names, columns=["id", "username", "password_hash", "role", "totp_secret"])

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
Use only the cybersecurity incident data in the current input. Base all analysis, conclusions, and recommendations only on that data and directly supported inferences. Do not use outside knowledge, prior context, current events, or unsupported assumptions.

ALLOWED KNOWLEDGE SOURCES:
- Current input data only
- Directly supported inferences

DISALLOWED BEHAVIOR:
- Do not answer beyond the data
- Do not invent facts, CVEs, malware, threat actors, exploit paths, MITRE mappings, or root causes
- Do not fill gaps or present assumptions as facts

REQUIRED OUT-OF-SCOPE RESPONSE:
"That cannot be determined from the provided incident data alone."
Optional:
"Please provide additional relevant data if you want a more specific answer."

You will receive incident CSV data with fields such as:
- index
- incident_id
- timestamp
- severity
- category
- status
- description

Your task is to analyze the data for end users and admins.

Objectives:
1. Identify trends over time
2. Detect anomalies or suspicious patterns
3. Highlight likely threats
4. Infer possible root causes where supported
5. Explain likely attack vectors only if supported
6. Use cybersecurity terms, MITRE ATT&CK, or CVEs only when supported
7. Prioritize actionable recommendations based on visible risk and impact
8. Keep findings useful for IT and understandable to non-experts

Instructions:
- Use only the provided data
- Separate:
  - direct observations
  - supported inferences
  - unknowns
- State limitations, assumptions, or confidence where needed
- Focus on recurring categories, severity patterns, unresolved incidents, time clusters, and signs of phishing, malware, unauthorized access, misconfiguration, insider risk, or lateral movement only if described
- Prioritize the biggest risks first
- If unsupported, say so clearly

Output format:
1. Executive Summary
2. Key Trends and Patterns
3. Anomalies and Suspicious Findings
4. Likely Threats and Attack Vectors
5. Root Cause Analysis
6. Prioritized Recommendations
7. Data Gaps / Confidence Notes

Style requirements:
- Professional and technical
- Concise but insightful
- Use bullets when helpful
- Prioritize recommendations clearly
- Avoid excess jargon for end users
""",

    "Data Science": """
Act as a senior data analyst and data quality advisor.

SCOPE RESTRICTION:
Use only the dataset metadata in the current input. Base all analysis, conclusions, and recommendations only on that metadata and directly supported inferences. Do not use outside knowledge, prior context, current events, or guesses about dataset contents.

ALLOWED KNOWLEDGE SOURCES:
- Current input metadata only
- Directly supported inferences

DISALLOWED BEHAVIOR:
- Do not assume column meanings, distributions, business definitions, or actual contents
- Do not invent data quality issues, statistics, or domain context
- Do not fill gaps or present assumptions as facts

REQUIRED OUT-OF-SCOPE RESPONSE:
"That cannot be determined from the provided metadata alone."
Optional:
"Please provide the dataset contents or additional metadata for a more specific answer."

You will receive metadata with fields such as:
- index
- dataset_id
- name
- rows
- columns
- uploaded_by
- upload_date

Your task is to analyze the metadata for users and admins.

Objectives:
1. Summarize what metadata supports
2. Suggest suitable statistical methods at a metadata-only level
3. Recommend visualizations based on likely structure and scale
4. Explain recommendation reasoning clearly
5. Flag possible quality risks suggested by metadata
6. Distinguish metadata facts from content-level unknowns
7. Recommend practical next steps

Instructions:
- Use only the provided metadata
- Separate:
  - confirmed observations
  - supported inferences
  - unknowns requiring data inspection
- State limitations clearly
- Infer likely complexity from size where useful
- Consider scale, freshness, maintenance, ownership, and usability
- Be practical, clear, and non-speculative
- If unsupported, say so clearly

Output format:
1. Overview
2. Metadata-Based Insights
3. Recommended Statistical Methods
4. Recommended Visualizations
5. Potential Data Quality Risks
6. Concrete Next Steps
7. Limitations and Assumptions

Style requirements:
- Professional and technical
- Clear and structured
- Use bullets when helpful
- Explain reasoning simply
- Avoid overclaiming
""",

    "IT Operations": """
Act as a senior IT service management analyst and technical support advisor.

SCOPE RESTRICTION:
Use only the IT ticket data in the current input. Base all analysis, conclusions, and recommendations only on that data and directly supported inferences. Do not use outside knowledge, prior context, current events, or unsupported technical assumptions.

ALLOWED KNOWLEDGE SOURCES:
- Current input ticket data only
- Directly supported inferences

DISALLOWED BEHAVIOR:
- Do not answer beyond the data
- Do not invent root causes, infrastructure details, versions, hardware specifics, or diagnoses
- Do not fill gaps or present assumptions as facts

REQUIRED OUT-OF-SCOPE RESPONSE:
"That cannot be determined from the provided ticket data alone."
Optional:
"Please provide additional ticket details or supporting operational data for a more specific answer."

You will receive IT ticket data with fields such as:
- index
- ticket_id
- priority
- description
- status
- assigned_to
- created_at
- resolution_time_hours

Your task is to analyze the ticket data for users and admins.

Objectives:
1. Identify high-priority issues
2. Detect recurring or systemic problems
3. Highlight operational bottlenecks
4. Suggest troubleshooting only when supported by ticket evidence
5. Recommend preventive measures tied to observed patterns
6. Distinguish urgent issues from long-term issues
7. Keep findings understandable to technical and general audiences

Instructions:
- Use only the provided data
- Separate:
  - direct observations
  - supported inferences
  - unknowns
- Use priority, status, timing, assignment, resolution time, and descriptions to assess impact
- State assumptions and confidence when descriptions are vague
- Look for repeated issues, long resolution times, unresolved tickets, overloaded assignees, time clusters, and signs of infrastructure, access, configuration, software, or hardware issues only if described
- Separate observations from recommendations
- Prioritize business-critical findings first
- If unsupported, say so clearly

Output format:
1. Executive Summary
2. Priority and Business Impact Assessment
3. Patterns and Systemic Issues
4. Troubleshooting Guidance
5. Preventive Measures
6. Operational Concerns
7. Limitations and Assumptions

Style requirements:
- Professional and technical
- Clear and structured
- Use bullets when helpful
- Keep recommendations practical and prioritized
- Avoid unnecessary jargon for general users
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
            placeholder = st.empty()
            full_reply = "" 
            try:
                response = client.chat.completions.create(
                    model="openai/gpt-oss-120b", messages=st.session_state[state_key], stream=True
                )
                
                for chunk in response:
                    delta = chunk.choices[0].delta.content
                    if delta: full_reply += delta; placeholder.write(full_reply + "▌ ")
                placeholder.write(full_reply)
                st.session_state[state_key].append({"role": "assistant", "content": full_reply})

            except groq.APIStatusError as e:
                placeholder.empty()
                st.session_state[state_key].pop()
                st.error("Request too large. Please clear the chat history to reduce message size and try again.")

            except groq.APIConnectionError as e:
                placeholder.empty()
                st.session_state[state_key].pop()
                st.error(f"Please check your internet connection and try again.")

            except Exception as e:
                placeholder.empty()
                st.session_state[state_key].pop()
                st.error("An unexpected error occurred.")


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
            st.session_state["profile_picture"] = default_profile()
            st.session_state["custom_profile"] = False
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
                st.session_state["custom_profile"] = True

        with col1:
            st.image(st.session_state["profile_picture"])

            if st.session_state.get("custom_profile", False):
                with col2:
                    if st.button("Remove"):
                        st.session_state["profile_picture"] = default_profile()
                        st.session_state["custom_profile"] = False
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

    # Logs out a user and redirects them to the home page
    st.divider()
    if st.button("Log out"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.info("You have been logged out.")
        st.switch_page(st.session_state.home)


def default_profile():
    img = Image.new("RGB", size=(150, 150), color=(0, 0, 0))

    draw = ImageDraw.Draw(img)
    draw.ellipse(
        xy=(35, 35, 100, 100),
        fill=(255, 255, 255),
        outline=(0, 0, 0),
        width=5
    )

    draw.ellipse(
        xy=(20, 110, 120, 185),
        fill=(255, 255, 255),
        outline=(0, 0, 0),
        width=5
    )

    img.format = "PNG"
    return img



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

if 'role' not in st.session_state:
    st.session_state.role = None

# ---------- Page Navigation ----------

pages = [home, login, register, cyber, datasets, it_dashboard, admin, account]
if st.session_state.logged_in:
    # Pages that can be accessed after a user is logged in
    pages = [cyber, datasets, it_dashboard, admin, account]

    with st.sidebar:
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.session_state.get("profile_picture") is not None:
                st.image(st.session_state["profile_picture"], width=100)
            else:
                st.image(default_profile(), width=100)
        with col2:
            st.markdown(f"**{st.session_state.username}**")
            st.caption(f"{st.session_state.role}")
        st.divider()
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
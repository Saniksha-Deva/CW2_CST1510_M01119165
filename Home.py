import streamlit as st
from hashing import generate_hash, is_valid_hash
from app_model.db import get_connection
from app_model.users import add_user, get_user, get_all_users, search_user, update_user, delete_user, update_user_role
from app_model.cyber_incidents import get_all_cyber_incidents
from app_model.metadatas import get_all_datasets_metadata
from app_model.it_tickets import get_all_it_tickets
import pandas as pd
import plotly.express as px


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

        # Get the user record from the database
        user = get_user(conn, login_username)

        if user is None:
            st.error("Incorrect username or password")
            return 
        
        id, user_name, user_hash, *_ = user

        # Verify the password against the stored hash
        if login_username and is_valid_hash(login_password, user_hash):
            st.session_state.logged_in = True
            st.session_state.username = user_name
            st.success("Logged in successfully!")
            # Redirect the user to the dashboard after logging in
            st.switch_page(cyber)
        else:
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
        hash_password = generate_hash(register_password)
        submitted = st.form_submit_button("Register")

        if submitted:
            if not register_username or not register_password:
                st.error("All fields are required.")
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

# ---------- Configure Pages for navigation ----------

home = st.Page(home_page, title="Home", icon="🏠")
login = st.Page(login_page, title="Login")
register = st.Page(register_page, title="Register")
dashboard = st.Page("pages/1_Dashboard.py", title="Dashboard")
cyber = st.Page(cyber_incidents_dashboard, title="Cyber Incidents Dashboard")
datasets = st.Page(datasets_dashboard, title="Datasets Metadata Dashboard")
it_dashboard = st.Page(it_tickets_dashboard, title="IT Tickets Dashboard")
admin = st.Page(admin_dashboard, title="Admin Dashboard")

st.session_state.home = home
st.session_state.login = login
st.session_state.register = register
st.session_state.dashboard = dashboard

# Make sure 'logged_in' exists in session state
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# ---------- Page Navigation ----------

pages = [home, login, register, dashboard, cyber, datasets, it_dashboard, admin]
if st.session_state.logged_in:
    # Pages that can be accessed after a user is logged in
    pages = [dashboard, cyber, datasets, it_dashboard, admin]

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


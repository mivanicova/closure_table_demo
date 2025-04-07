# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import pandas as pd

from models import ClosureTable
from views import AdminView, UserView
from text_interface import TextInterface
from utils import get_file_id

def main():
    """Main application entry point."""
    # Set page title
    st.set_page_config(page_title="Dátová Mapa", layout="wide")
    
    # Initialize session state
    if 'processed_file_ids' not in st.session_state:
        st.session_state.processed_file_ids = set()
    
    # Initialize closure tables
    if 'admin_closure_table' not in st.session_state:
        st.session_state.admin_closure_table = ClosureTable.create_default_admin_table()
    
    if 'user_closure_table' not in st.session_state:
        st.session_state.user_closure_table = ClosureTable.create_empty_user_table()
    
    # Výber režimu zobrazenia
    page = st.sidebar.radio("Režim:", ["Administrátor", "Používateľ"])
    
    # Handle file upload
    handle_file_upload()
    
    # Render the appropriate view
    if page == "Administrátor":
        admin_view = AdminView(st.session_state.admin_closure_table)
        admin_view.render()
    elif page == "Používateľ":
        user_view = UserView(
            st.session_state.admin_closure_table,
            st.session_state.user_closure_table
        )
        user_view.render()
    
    # Option to show raw tables
    show_raw_tables()

def handle_file_upload():
    """Handle file upload for admin and user closure tables."""
    # Admin file upload
    with st.sidebar.expander("Admin súbory", expanded=False):
        uploaded_admin_file = st.file_uploader("Nahraj admin closure_table (CSV)", type="csv", key="admin_uploader")
        
        if uploaded_admin_file is not None:
            file_id = get_file_id(uploaded_admin_file)
            
            if file_id not in st.session_state.processed_file_ids:
                df = pd.read_csv(uploaded_admin_file)
                st.session_state.admin_closure_table = ClosureTable(df)
                
                # Synchronize user table with the newly uploaded admin table
                if 'user_closure_table' in st.session_state:
                    st.session_state.user_closure_table = st.session_state.user_closure_table.synchronize_with(
                        st.session_state.admin_closure_table
                    )
                
                st.session_state.working_file_id = file_id
                st.session_state.processed_file_ids = {file_id}
                st.success("Admin closure_table úspešne nahraný!")
                st.rerun()
    
    # User file upload
    with st.sidebar.expander("Používateľské súbory", expanded=False):
        uploaded_user_file = st.file_uploader("Nahraj používateľský closure_table (CSV)", type="csv", key="user_uploader")
        
        if uploaded_user_file is not None:
            file_id = get_file_id(uploaded_user_file)
            
            if file_id not in st.session_state.processed_file_ids:
                df = pd.read_csv(uploaded_user_file)
                
                # Create a new ClosureTable from the uploaded file
                user_table = ClosureTable(df)
                
                # Synchronize with the admin table to ensure consistency
                user_table = user_table.synchronize_with(st.session_state.admin_closure_table)
                
                # Update the session state
                st.session_state.user_closure_table = user_table
                st.session_state.working_file_id = file_id
                st.session_state.processed_file_ids = {file_id}
                st.success("Používateľský closure_table úspešne nahraný!")
                st.rerun()

def show_raw_tables():
    """Show raw closure tables if requested."""
    show_table = st.checkbox("Zobraziť closure_table", value=st.session_state.get('show_table', False))
    st.session_state.show_table = show_table
    
    if show_table:
        st.subheader("Admin closure table")
        st.dataframe(st.session_state.admin_closure_table.to_dataframe())
        
        st.subheader("Používateľská closure table")
        st.dataframe(st.session_state.user_closure_table.to_dataframe())

if __name__ == "__main__":
    main()

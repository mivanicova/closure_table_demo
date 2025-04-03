import streamlit as st
import pandas as pd

from models import ClosureTable
from views import AdminView, UserView
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
    """Handle file upload for admin closure table."""
    uploaded_file = st.sidebar.file_uploader("Nahraj admin closure_table (CSV)", type="csv")
    
    if uploaded_file is not None:
        file_id = get_file_id(uploaded_file)
        
        if file_id not in st.session_state.processed_file_ids:
            df = pd.read_csv(uploaded_file)
            st.session_state.admin_closure_table = ClosureTable(df)
            
            # Synchronize user table with the newly uploaded admin table
            if 'user_closure_table' in st.session_state:
                st.session_state.user_closure_table = st.session_state.user_closure_table.synchronize_with(
                    st.session_state.admin_closure_table
                )
            
            st.session_state.working_file_id = file_id
            st.session_state.processed_file_ids = {file_id}
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

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
from streamlit_tree_select import tree_select

from models import ClosureTable
from utils import convert_df_to_csv, compute_completion_score, build_tree_data

class BaseView:
    """Base class for views with common functionality."""
    
    @staticmethod
    def render_graph(closure_table):
        """Render a graph visualization of the closure table.
        
        Args:
            closure_table: ClosureTable instance
        """
        unique_nodes = closure_table.get_unique_nodes()
        nodes = [
            Node(
                id=row['descendant'], 
                label=row['descendant'], 
                color="red" if row['is_descendant_koko'] else "#97C2FC"
            ) 
            for _, row in unique_nodes.iterrows()
        ]
        
        direct_edges = closure_table.get_direct_edges()
        edges = [
            Edge(source=row['ancestor'], target=row['descendant']) 
            for _, row in direct_edges.iterrows()
        ]
        
        config = Config(
            width=700, 
            height=500, 
            directed=True, 
            nodeHighlightBehavior=True, 
            highlightColor="#F7A7A6"
        )
        
        agraph(nodes=nodes, edges=edges, config=config)


class AdminView(BaseView):
    """View for administrator mode."""
    
    def __init__(self, admin_table):
        """Initialize AdminView with a closure table.
        
        Args:
            admin_table: ClosureTable instance for admin data
        """
        self.admin_table = admin_table
    
    def render(self):
        """Render the administrator view."""
        st.sidebar.header("Správa stromu")
        action = st.sidebar.selectbox("Akcia:", ["Pridať nový uzol", "Zmazať uzol", "Presunúť uzol"])
        
        if action == "Pridať nový uzol":
            self._render_add_node()
        elif action == "Zmazať uzol":
            self._render_delete_node()
        elif action == "Presunúť uzol":
            self._render_move_node()
        
        st.header("Vizualizácia dátovej mapy (admin)")
        self.render_graph(self.admin_table)
        
        # Download button for admin table
        admin_csv = convert_df_to_csv(self.admin_table.to_dataframe())
        st.sidebar.download_button(
            label="Stiahnuť admin closure_table ako CSV",
            data=admin_csv,
            file_name='admin_closure_table.csv',
            mime='text/csv'
        )
    
    def _render_add_node(self):
        """Render the UI for adding a new node."""
        selected_parent = st.sidebar.selectbox(
            "Vyber rodiča:", 
            self.admin_table.get_all_nodes()
        )
        new_node_name = st.sidebar.text_input("Meno nového uzla:")
        
        if st.sidebar.button("Pridaj nový uzol"):
            if new_node_name.strip():
                self.admin_table.add_node(
                    selected_parent,
                    new_node_name.strip(),
                    is_descendant_koko=True,
                    is_user_defined=False
                )
                st.sidebar.success(f"Uzol '{new_node_name}' pridaný pod '{selected_parent}'!")
                st.rerun()
            else:
                st.sidebar.error("Zadaj názov nového uzla!")
    
    def _render_delete_node(self):
        """Render the UI for deleting a node."""
        node_to_delete = st.sidebar.selectbox(
            "Vyber uzol na zmazanie:", 
            self.admin_table.get_all_nodes()
        )
        
        if st.sidebar.button("Zmaž uzol"):
            self.admin_table.delete_node(node_to_delete)
            st.sidebar.success(f"Uzol '{node_to_delete}' a jeho potomkovia boli zmazaní!")
            st.rerun()
    
    def _render_move_node(self):
        """Render the UI for moving a node."""
        all_nodes = self.admin_table.get_all_nodes()
        node_to_move = st.sidebar.selectbox("Vyber uzol na presun:", all_nodes)
        
        possible_parents = list(all_nodes)
        if node_to_move in possible_parents:
            possible_parents.remove(node_to_move)
        
        new_parent = st.sidebar.selectbox("Vyber nový rodič:", possible_parents)
        
        if st.sidebar.button("Presuň uzol"):
            try:
                self.admin_table.move_node(node_to_move, new_parent)
                st.sidebar.success(f"Uzol '{node_to_move}' bol presunutý pod '{new_parent}'!")
                st.rerun()
            except ValueError as e:
                st.sidebar.error(str(e))


class UserView(BaseView):
    """View for user mode."""
    
    def __init__(self, admin_table, user_table):
        """Initialize UserView with admin and user closure tables.
        
        Args:
            admin_table: ClosureTable instance for admin data
            user_table: ClosureTable instance for user data
        """
        self.admin_table = admin_table
        self.user_table = user_table
        self.combined_table = admin_table.merge(user_table)
    
    def render(self):
        """Render the user view."""
        st.sidebar.header("Moje uzly")
        st.sidebar.header("Pridaj svoj uzol")
        
        self._render_add_user_node()
        self._render_delete_user_node()
        
        # Interactive tree structure
        st.subheader("🌳 Interaktívna stromová štruktúra")
        tree_data = build_tree_data(self.combined_table.to_dataframe())
        selected = tree_select(tree_data)
        
        if selected:
            st.success(f"Vybraný uzol: {selected}")
        
        # Visualization
        st.header("Vizualizácia dátovej mapy (používateľ)")
        self.render_graph(self.combined_table)
        
        # Completion score
        total, completed = compute_completion_score(self.combined_table.to_dataframe())
        st.markdown(f"### Skóre vyplnenosti stromu: {completed} / {total} koncových KoKo uzlov má potomkov")
    
    def _render_add_user_node(self):
        """Render the UI for adding a user node."""
        admin_nodes = self.admin_table.get_all_nodes()
        user_defined_nodes = self.user_table.get_user_defined_nodes()
        valid_parents = [node for node in admin_nodes if node not in user_defined_nodes]
        
        if valid_parents:
            selected_parent = st.sidebar.selectbox("Vyber rodiča:", valid_parents)
            new_node_name = st.sidebar.text_input("Názov môjho uzla:")
            
            if st.sidebar.button("Pridať môj uzol"):
                if new_node_name.strip():
                    merged_table = self.admin_table.merge(self.user_table)
                    updated_table = merged_table.add_node(
                        selected_parent,
                        new_node_name.strip(),
                        is_descendant_koko=False,
                        is_user_defined=True
                    )
                    
                    # Update both the instance variable and the session state
                    self.user_table = ClosureTable(updated_table.to_dataframe())
                    st.session_state.user_closure_table = self.user_table
                    
                    st.sidebar.success(f"Tvoj uzol '{new_node_name}' bol pridaný pod '{selected_parent}'!")
                    st.rerun()
                else:
                    st.sidebar.error("Zadaj názov svojho uzla!")
        else:
            st.sidebar.info("Nie sú dostupní žiadni platní rodičia.")
    
    def _render_delete_user_node(self):
        """Render the UI for deleting a user node."""
        deletable_nodes = self.user_table.get_user_defined_nodes()
        
        if len(deletable_nodes) > 0:
            st.sidebar.markdown("---")
            st.sidebar.subheader("Zmaž svoj uzol")
            node_to_delete = st.sidebar.selectbox("Vyber uzol na zmazanie:", deletable_nodes)
            
            if st.sidebar.button("Zmaž môj uzol"):
                self.user_table.delete_node(node_to_delete)
                # Update the session state
                st.session_state.user_closure_table = self.user_table
                st.sidebar.success(f"Uzol '{node_to_delete}' bol zmazaný.")
                st.rerun()

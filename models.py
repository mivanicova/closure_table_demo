import pandas as pd
import streamlit as st
import json

class ClosureTable:
    """Class for managing a closure table representation of a hierarchical structure."""
    
    def __init__(self, df=None):
        """Initialize a ClosureTable with optional DataFrame.
        
        Args:
            df: Optional DataFrame with closure table data
        """
        if df is not None:
            # Add node_type column if it doesn't exist
            if 'node_type' not in df.columns:
                df['node_type'] = None
            # Add attributes column if it doesn't exist
            if 'attributes' not in df.columns:
                df['attributes'] = None
            self.df = df
        else:
            self.df = pd.DataFrame(
                columns=['ancestor', 'descendant', 'depth', 'is_descendant_koko', 'is_user_defined', 'node_type', 'attributes']
            )
    
    @classmethod
    def create_default_admin_table(cls):
        """Create a default admin closure table with initial data."""
        return cls(pd.DataFrame([
            {'ancestor': 'Zem', 'descendant': 'Zem', 'depth': 0, 'is_descendant_koko': True, 'is_user_defined': False, 'node_type': 'Koncept alebo doménová téma', 'attributes': '{}'},
            {'ancestor': 'Zem', 'descendant': 'Živé', 'depth': 1, 'is_descendant_koko': True, 'is_user_defined': False, 'node_type': 'Koncept alebo doménová téma', 'attributes': '{}'},
            {'ancestor': 'Živé', 'descendant': 'Živé', 'depth': 0, 'is_descendant_koko': True, 'is_user_defined': False, 'node_type': 'Koncept alebo doménová téma', 'attributes': '{}'},
        ]))
    
    @classmethod
    def create_empty_user_table(cls):
        """Create an empty user closure table."""
        return cls()
    
    def add_node(self, parent, new_node, is_descendant_koko=False, is_user_defined=True, node_type=None, attributes=None):
        """Add a new node to the closure table.
        
        Args:
            parent: Parent node name
            new_node: New node name
            is_descendant_koko: Whether the node is a KoKo descendant
            is_user_defined: Whether the node is user-defined
            node_type: Type of the node (Osoba, Miesto, Koncept, Digitálny obsah, Iné)
            attributes: Dictionary of node attributes
            
        Returns:
            ClosureTable: Updated closure table
        """
        # Convert attributes to JSON string if provided
        attributes_json = '{}'
        if attributes:
            try:
                attributes_json = json.dumps(attributes, ensure_ascii=False)
            except Exception as e:
                st.error(f"Error converting attributes to JSON: {e}")
        
        new_entries = []
        ancestors = self.df[self.df['descendant'] == parent]
        
        for _, ancestor_row in ancestors.iterrows():
            new_entries.append({
                'ancestor': ancestor_row['ancestor'],
                'descendant': new_node,
                'depth': ancestor_row['depth'] + 1,
                'is_descendant_koko': is_descendant_koko,
                'is_user_defined': is_user_defined,
                'node_type': node_type,
                'attributes': attributes_json
            })
        
        new_entries.append({
            'ancestor': new_node,
            'descendant': new_node,
            'depth': 0,
            'is_descendant_koko': is_descendant_koko,
            'is_user_defined': is_user_defined,
            'node_type': node_type,
            'attributes': attributes_json
        })
        
        self.df = pd.concat([self.df, pd.DataFrame(new_entries)], ignore_index=True)
        return self
    
    def delete_node(self, node_to_delete):
        """Delete a node and all its descendants from the closure table.
        
        Args:
            node_to_delete: Node to delete
            
        Returns:
            ClosureTable: Updated closure table
        """
        descendants = self.df[self.df['ancestor'] == node_to_delete]['descendant'].tolist()
        self.df = self.df[~self.df['descendant'].isin(descendants) & ~self.df['ancestor'].isin(descendants)]
        return self
    
    def move_node(self, node_to_move, new_parent):
        """Move a node to a new parent in the closure table.
        
        Args:
            node_to_move: Node to move
            new_parent: New parent node
            
        Returns:
            ClosureTable: Updated closure table
            
        Raises:
            ValueError: If the move operation is invalid
        """
        # Check if node is a root node that can't be moved
        is_root = self.df[(self.df['ancestor'] == node_to_move) & (self.df['depth'] == 0)].shape[0] == 1
        has_no_ancestors = self.df[(self.df['descendant'] == node_to_move) & (self.df['depth'] > 0)].empty
        
        if is_root and has_no_ancestors:
            raise ValueError(f"Uzol '{node_to_move}' je root uzol a nemôže byť presunutý.")

        # Check if trying to move a node under its own descendant
        descendants_of_node = self.df[self.df['ancestor'] == node_to_move]['descendant'].unique().tolist()
        if new_parent in descendants_of_node:
            raise ValueError(f"Uzol '{node_to_move}' nemôže byť presunutý pod svojho potomka '{new_parent}'!")

        # Get all descendants of the node being moved (including the node itself)
        subtree_nodes = descendants_of_node

        # Get all paths that involve the node being moved and its descendants
        # These are the paths we need to remove and recreate
        paths_to_remove = self.df[
            (self.df['descendant'].isin(subtree_nodes)) & 
            (~self.df['ancestor'].isin(subtree_nodes) | (self.df['ancestor'] == node_to_move))
        ].copy()
        
        # Keep track of the internal structure of the subtree (relationships between nodes in the subtree)
        internal_subtree = self.df[
            (self.df['ancestor'].isin(subtree_nodes)) & 
            (self.df['descendant'].isin(subtree_nodes)) &
            (self.df['ancestor'] != node_to_move)
        ].copy()
        
        # Remove the paths that need to be recreated
        self.df = self.df[~(
            (self.df['descendant'].isin(subtree_nodes)) & 
            (~self.df['ancestor'].isin(subtree_nodes) | (self.df['ancestor'] == node_to_move))
        )]
        
        # Get all ancestors of the new parent (including the new parent itself)
        new_parent_ancestors = self.df[self.df['descendant'] == new_parent].copy()
        
        # Create new paths from each ancestor of new_parent to each node in the subtree
        new_paths = []
        
        # For each ancestor of the new parent
        for _, ancestor_row in new_parent_ancestors.iterrows():
            # For each node in the subtree
            for subtree_node in subtree_nodes:
                # Find the depth of this node relative to the node_to_move
                relative_depth = 0
                if subtree_node != node_to_move:
                    # Get the path from node_to_move to this subtree node
                    path = paths_to_remove[
                        (paths_to_remove['ancestor'] == node_to_move) & 
                        (paths_to_remove['descendant'] == subtree_node)
                    ]
                    if not path.empty:
                        relative_depth = path.iloc[0]['depth']
                
                # Create a new path from the ancestor to this subtree node
                # Get the node properties from the original paths
                node_props = paths_to_remove[paths_to_remove['descendant'] == subtree_node]
                
                if not node_props.empty:
                    props = node_props.iloc[0]
                    new_paths.append({
                        'ancestor': ancestor_row['ancestor'],
                        'descendant': subtree_node,
                        'depth': ancestor_row['depth'] + relative_depth,
                        'is_descendant_koko': props.get('is_descendant_koko', False),
                        'is_user_defined': props.get('is_user_defined', False),
                        'node_type': props.get('node_type', None),
                        'attributes': props.get('attributes', '{}')
                    })
        
        # Add the new paths to the DataFrame
        if new_paths:
            self.df = pd.concat([self.df, pd.DataFrame(new_paths)], ignore_index=True)
        
        # Add back the internal subtree structure
        if not internal_subtree.empty:
            self.df = pd.concat([self.df, internal_subtree], ignore_index=True)
        
        # Remove any duplicates that might have been created
        self.df = self.df.drop_duplicates()
        return self
    
    def get_unique_nodes(self):
        """Get all unique nodes in the closure table.
        
        Returns:
            DataFrame: DataFrame with unique nodes and their properties
        """
        return self.df[['descendant', 'is_descendant_koko', 'node_type', 'attributes']].drop_duplicates()
    
    def get_direct_edges(self):
        """Get all direct edges (parent-child relationships) in the closure table.
        
        Returns:
            DataFrame: DataFrame with direct edges
        """
        return self.df[self.df['depth'] == 1]
    
    def get_all_nodes(self):
        """Get all unique node names in the closure table.
        
        Returns:
            array: Array of unique node names
        """
        return self.df['descendant'].unique()
    
    def get_user_defined_nodes(self):
        """Get all user-defined nodes in the closure table.
        
        Returns:
            array: Array of user-defined node names
        """
        return self.df[self.df['is_user_defined'] == True]['descendant'].unique()
    
    def merge(self, other_table):
        """Merge this closure table with another closure table.
        
        Args:
            other_table: Another ClosureTable instance
            
        Returns:
            ClosureTable: New merged closure table
        """
        merged_df = pd.concat([self.df, other_table.df]).drop_duplicates()
        return ClosureTable(merged_df)
    
    def synchronize_with(self, admin_table):
        """Synchronize this user table with changes in the admin table.
        
        This method updates the user table to reflect changes in the admin table:
        - If a node in the admin table is moved, the same node in the user table is moved
        - If a node in the admin table is deleted, the same node in the user table is deleted
        - User-defined nodes (is_user_defined=True) are preserved
        
        Args:
            admin_table: The admin ClosureTable to synchronize with
            
        Returns:
            ClosureTable: Updated user table
        """
        # Get all nodes in both tables
        admin_nodes = set(admin_table.get_all_nodes())
        user_nodes = set(self.get_all_nodes())
        
        # Find nodes that exist in both tables
        common_nodes = admin_nodes.intersection(user_nodes)
        
        # Create a new DataFrame for the updated user table
        new_df = self.df.copy()
        
        # Get user-defined nodes
        user_defined_nodes = set(self.get_user_defined_nodes())
        
        # For each common node, update its relationships in the user table
        # based on its relationships in the admin table
        for node in common_nodes:
            # Skip user-defined nodes - we want to preserve these
            if node in user_defined_nodes:
                continue
                
            # Get all ancestors and descendants of the node in the admin table
            admin_ancestors = admin_table.df[admin_table.df['descendant'] == node]['ancestor'].tolist()
            admin_descendants = admin_table.df[admin_table.df['ancestor'] == node]['descendant'].tolist()
            
            # Remove all relationships involving this node from the user table
            # but only if it's not a user-defined node
            new_df = new_df[~(((new_df['ancestor'] == node) | (new_df['descendant'] == node)) & 
                             ~new_df['descendant'].isin(user_defined_nodes))]
            
            # Add the relationships from the admin table to the user table
            admin_node_relations = admin_table.df[(admin_table.df['ancestor'] == node) | 
                                                 (admin_table.df['descendant'] == node)].copy()
            
            # Preserve the is_user_defined flag as False for admin-inherited nodes
            admin_node_relations['is_user_defined'] = False
            
            # Filter out any relationships where the descendant is a user-defined node
            # as we want to preserve the user's relationships for these nodes
            admin_node_relations = admin_node_relations[~admin_node_relations['descendant'].isin(user_defined_nodes)]
            
            new_df = pd.concat([new_df, admin_node_relations], ignore_index=True)
        
        # Remove any nodes that exist in the user table but not in the admin table
        # (they might have been deleted from the admin table)
        user_only_nodes = user_nodes - admin_nodes
        for node in user_only_nodes:
            # Skip user-defined nodes - we want to preserve these
            if node in user_defined_nodes:
                continue
                
            if not self.df[self.df['descendant'] == node]['is_user_defined'].any():
                # If this is not a user-defined node, remove it
                new_df = new_df[~((new_df['ancestor'] == node) | (new_df['descendant'] == node))]
        
        return ClosureTable(new_df.drop_duplicates())
    
    def to_dataframe(self):
        """Convert the closure table to a DataFrame.
        
        Returns:
            DataFrame: The closure table as a DataFrame
        """
        return self.df

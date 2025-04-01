import pandas as pd
import streamlit as st

class ClosureTable:
    """Class for managing a closure table representation of a hierarchical structure."""
    
    def __init__(self, df=None):
        """Initialize a ClosureTable with optional DataFrame.
        
        Args:
            df: Optional DataFrame with closure table data
        """
        self.df = df if df is not None else pd.DataFrame(
            columns=['ancestor', 'descendant', 'depth', 'is_descendant_koko', 'is_user_defined']
        )
    
    @classmethod
    def create_default_admin_table(cls):
        """Create a default admin closure table with initial data."""
        return cls(pd.DataFrame([
            {'ancestor': 'Zem', 'descendant': 'Zem', 'depth': 0, 'is_descendant_koko': True, 'is_user_defined': False},
            {'ancestor': 'Zem', 'descendant': 'Živé', 'depth': 1, 'is_descendant_koko': True, 'is_user_defined': False},
            {'ancestor': 'Živé', 'descendant': 'Živé', 'depth': 0, 'is_descendant_koko': True, 'is_user_defined': False},
        ]))
    
    @classmethod
    def create_empty_user_table(cls):
        """Create an empty user closure table."""
        return cls()
    
    def add_node(self, parent, new_node, is_descendant_koko=False, is_user_defined=True):
        """Add a new node to the closure table.
        
        Args:
            parent: Parent node name
            new_node: New node name
            is_descendant_koko: Whether the node is a KoKo descendant
            is_user_defined: Whether the node is user-defined
            
        Returns:
            ClosureTable: Updated closure table
        """
        new_entries = []
        ancestors = self.df[self.df['descendant'] == parent]
        
        for _, ancestor_row in ancestors.iterrows():
            new_entries.append({
                'ancestor': ancestor_row['ancestor'],
                'descendant': new_node,
                'depth': ancestor_row['depth'] + 1,
                'is_descendant_koko': is_descendant_koko,
                'is_user_defined': is_user_defined
            })
        
        new_entries.append({
            'ancestor': new_node,
            'descendant': new_node,
            'depth': 0,
            'is_descendant_koko': is_descendant_koko,
            'is_user_defined': is_user_defined
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
        is_root = self.df[(self.df['ancestor'] == node_to_move) & (self.df['depth'] == 0)].shape[0] == 1
        has_no_ancestors = self.df[(self.df['descendant'] == node_to_move) & (self.df['depth'] > 0)].empty
        
        if is_root and has_no_ancestors:
            raise ValueError(f"Uzol '{node_to_move}' je root uzol a nemôže byť presunutý.")

        descendants_of_node = self.df[self.df['ancestor'] == node_to_move]['descendant'].tolist()
        if new_parent in descendants_of_node:
            raise ValueError(f"Uzol '{node_to_move}' nemôže byť presunutý pod svojho potomka '{new_parent}'!")

        subtree = self.df[self.df['ancestor'] == node_to_move].copy()
        subtree_descendants = subtree['descendant'].unique().tolist()
        ancestors = self.df[self.df['descendant'] == node_to_move]['ancestor'].unique().tolist()

        self.df = self.df[~(
            self.df['ancestor'].isin(ancestors) &
            self.df['descendant'].isin(subtree_descendants) &
            (self.df['ancestor'] != self.df['descendant'])
        )]

        new_ancestors = self.df[self.df['descendant'] == new_parent].copy()

        new_paths = []
        for _, ancestor_row in new_ancestors.iterrows():
            for _, sub_row in subtree.iterrows():
                new_paths.append({
                    'ancestor': ancestor_row['ancestor'],
                    'descendant': sub_row['descendant'],
                    'depth': ancestor_row['depth'] + 1 + sub_row['depth'],
                    'is_descendant_koko': sub_row.get('is_descendant_koko', False),
                    'is_user_defined': sub_row.get('is_user_defined', False)
                })

        new_paths += subtree.to_dict('records')
        self.df = pd.concat([self.df, pd.DataFrame(new_paths)], ignore_index=True)
        self.df = self.df.drop_duplicates()
        return self
    
    def get_unique_nodes(self):
        """Get all unique nodes in the closure table.
        
        Returns:
            DataFrame: DataFrame with unique nodes and their properties
        """
        return self.df[['descendant', 'is_descendant_koko']].drop_duplicates()
    
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
    
    def to_dataframe(self):
        """Convert the closure table to a DataFrame.
        
        Returns:
            DataFrame: The closure table as a DataFrame
        """
        return self.df

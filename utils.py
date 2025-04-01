import hashlib
import pandas as pd
import streamlit as st

def get_file_id(uploaded_file):
    """Compute a unique file identifier for an uploaded file."""
    return hashlib.md5(f"{uploaded_file.name}{uploaded_file.size}".encode()).hexdigest()

@st.cache_data
def convert_df_to_csv(df):
    """Convert a DataFrame to CSV format for download."""
    return df.to_csv(index=False).encode('utf-8')

def compute_completion_score(df):
    """Compute the completion score for the tree.
    
    Returns:
        tuple: (total, completed) where total is the total number of end nodes
               and completed is the number of end nodes that have descendants.
    """
    koko_nodes = df[df['is_descendant_koko'] == True]['descendant'].unique()
    koko_parents = df[(df['is_descendant_koko'] == True) & (df['depth'] == 1) & (df['ancestor'].isin(koko_nodes))]['ancestor'].unique()
    end_nodes = [n for n in koko_nodes if n not in koko_parents]
    total = len(end_nodes)
    completed = 0
    for node in end_nodes:
        has_descendant = not df[(df['ancestor'] == node) & (df['depth'] == 1)].empty
        if has_descendant:
            completed += 1
    return total, completed

def build_tree(df):
    """Build a tree structure from a closure table.
    
    Args:
        df: DataFrame with closure table data
        
    Returns:
        tuple: (tree, children_set) where tree is a dictionary mapping parents to children
               and children_set is a set of all child nodes
    """
    tree = {}
    children_set = set()

    for _, row in df[df['depth'] == 1].iterrows():
        parent, child = row['ancestor'], row['descendant']
        tree.setdefault(parent, []).append(child)
        children_set.add(child)

    return tree, children_set

def render_tree_sorted(tree, node, level=0, visited=None):
    """Render a tree structure in a sorted manner.
    
    Args:
        tree: Dictionary mapping parents to children
        node: Current node to render
        level: Current indentation level
        visited: Set of visited nodes to prevent cycles
    """
    if visited is None:
        visited = set()

    if node in visited:
        return
    visited.add(node)

    children = sorted(tree.get(node, []))
    indent = " " * level
    icon = "📁" if children else "📄"
    st.markdown(f"{indent}{icon} {node}")

    for child in children:
        render_tree_sorted(tree, child, level + 1, visited)

def build_tree_data(df):
    """Build tree data for streamlit_tree_select component.
    
    Args:
        df: DataFrame with closure table data
        
    Returns:
        list: List of tree nodes in the format required by streamlit_tree_select
    """
    tree = {}
    for _, row in df[df['depth'] == 1].iterrows():
        parent, child = row['ancestor'], row['descendant']
        tree.setdefault(parent, set()).add(child)

    def build_subtree(node):
        children = tree.get(node, [])
        return {
            "label": node,
            "value": node,
            "children": [build_subtree(child) for child in sorted(children)]
        }

    # Find root nodes: those that are not descendants of any other node
    all_nodes = set(df['descendant'].unique())
    child_nodes = set(df[df['depth'] == 1]['descendant'].unique())
    roots = list(all_nodes - child_nodes)

    return [build_subtree(root) for root in sorted(roots)]

import hashlib
import json
import os
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
    # Create a dictionary to store node properties
    node_properties = {}
    
    # Check if the required columns exist in the DataFrame
    has_user_defined = 'is_user_defined' in df.columns
    has_node_type = 'node_type' in df.columns
    has_attributes = 'attributes' in df.columns
    
    # Extract unique nodes with their properties
    columns = ['descendant']
    if has_user_defined:
        columns.append('is_user_defined')
    if has_node_type:
        columns.append('node_type')
    if has_attributes:
        columns.append('attributes')
    
    unique_nodes = df[columns].drop_duplicates()
    for _, row in unique_nodes.iterrows():
        props = {
            'is_user_defined': row.get('is_user_defined', False) if has_user_defined else False,
            'node_type': row.get('node_type', None) if has_node_type else None,
            'attributes': row.get('attributes', '{}') if has_attributes else '{}'
        }
        node_properties[row['descendant']] = props
    
    # Build the tree structure
    for _, row in df[df['depth'] == 1].iterrows():
        parent, child = row['ancestor'], row['descendant']
        tree.setdefault(parent, set()).add(child)

    def build_subtree(node):
        children = tree.get(node, [])
        props = node_properties.get(node, {})
        is_user_defined = props.get('is_user_defined', False)
        node_type = props.get('node_type', 'Neurčený')
        
        # Create label with visual indicators for user_defined status
        if is_user_defined:
            label = f"🟢 {node}"  # Green circle for user-defined nodes
        else:
            label = f"🔴 {node}"  # Red circle for non-user-defined nodes
        
        # Add node type if available
        if node_type:
            label = f"{label} [Typ: {node_type}]"
        
        return {
            "label": label,
            "value": node,
            "children": [build_subtree(child) for child in sorted(children)],
            "is_user_defined": is_user_defined,
            "node_type": node_type,
            "attributes": props.get('attributes', '{}')
        }

    # Find root nodes: those that are not descendants of any other node
    all_nodes = set(df['descendant'].unique())
    child_nodes = set(df[df['depth'] == 1]['descendant'].unique())
    roots = list(all_nodes - child_nodes)

    return [build_subtree(root) for root in sorted(roots)]

@st.cache_data
def load_object_types():
    """Load object types from the JSON file.
    
    Returns:
        dict: Dictionary of object types
    """
    file_path = os.path.join(os.path.dirname(__file__), 'object_types.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading object types: {e}")
        return {}

def get_object_type_names():
    """Get a list of object type names.
    
    Returns:
        list: List of object type names
    """
    object_types = load_object_types()
    return [object_types[key]['name'] for key in object_types]

def get_object_type_by_name(name):
    """Get an object type by its display name.
    
    Args:
        name: Display name of the object type
        
    Returns:
        tuple: (key, object_type) where key is the object type key and object_type is the object type data
    """
    object_types = load_object_types()
    for key, obj_type in object_types.items():
        if obj_type['name'] == name:
            return key, obj_type
    return None, None

def get_object_type_color(name):
    """Get the color for an object type.
    
    Args:
        name: Display name of the object type
        
    Returns:
        str: Color code for the object type
    """
    _, obj_type = get_object_type_by_name(name)
    if obj_type:
        return obj_type.get('color', '#CCCCCC')
    return '#CCCCCC'

def get_object_type_attributes(name):
    """Get the attributes for an object type.
    
    Args:
        name: Display name of the object type
        
    Returns:
        list: List of attribute definitions
    """
    _, obj_type = get_object_type_by_name(name)
    if obj_type:
        return obj_type.get('attributes', [])
    return []

def save_object_types(object_types):
    """Save object types to the JSON file.
    
    Args:
        object_types: Dictionary of object types
    """
    file_path = os.path.join(os.path.dirname(__file__), 'object_types.json')
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(object_types, f, indent=2, ensure_ascii=False)
        # Clear the cache to reload the object types
        load_object_types.clear()
    except Exception as e:
        st.error(f"Error saving object types: {e}")

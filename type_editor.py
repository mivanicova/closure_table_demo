import streamlit as st
import json
import os
from utils import load_object_types, save_object_types

def render_type_editor():
    """Render the object type editor UI."""
    st.title("Editor typov objektov")
    
    # Load object types
    object_types = load_object_types()
    
    # Sidebar for selecting action
    action = st.sidebar.selectbox(
        "Akcia:",
        ["Zobraziť typy", "Upraviť typ", "Pridať nový typ"]
    )
    
    if action == "Zobraziť typy":
        _render_view_types(object_types)
    elif action == "Upraviť typ":
        _render_edit_type(object_types)
    elif action == "Pridať nový typ":
        _render_add_type(object_types)

def _render_view_types(object_types):
    """Render the view for displaying all object types."""
    st.header("Dostupné typy objektov")
    
    for key, obj_type in object_types.items():
        with st.expander(f"{obj_type['name']} ({key})"):
            st.markdown(f"**Farba:** {obj_type['color']}")
            
            st.markdown("**Atribúty:**")
            if not obj_type.get('attributes'):
                st.info("Žiadne atribúty")
            else:
                for attr in obj_type['attributes']:
                    required = "✓" if attr.get('required', False) else "✗"
                    st.markdown(f"- **{attr['name']}** ({attr['type']}, Povinné: {required})")
                    if attr.get('description'):
                        st.markdown(f"  *{attr['description']}*")

def _render_edit_type(object_types):
    """Render the view for editing an existing object type."""
    st.header("Upraviť typ objektu")
    
    # Select type to edit
    type_names = [(key, obj_type['name']) for key, obj_type in object_types.items()]
    selected_key = st.selectbox(
        "Vyber typ na úpravu:",
        [key for key, _ in type_names],
        format_func=lambda key: next((name for k, name in type_names if k == key), key)
    )
    
    if selected_key:
        obj_type = object_types[selected_key]
        
        # Edit basic properties
        new_name = st.text_input("Názov typu:", obj_type['name'])
        new_color = st.color_picker("Farba:", obj_type['color'])
        
        # Edit attributes
        st.subheader("Atribúty")
        attributes = obj_type.get('attributes', [])
        
        updated_attributes = []
        for i, attr in enumerate(attributes):
            with st.expander(f"Atribút: {attr['name']}"):
                attr_name = st.text_input("Názov atribútu:", attr['name'], key=f"name_{i}")
                attr_type = st.selectbox(
                    "Typ atribútu:",
                    ["string", "number", "integer", "boolean", "object", "array"],
                    index=["string", "number", "integer", "boolean", "object", "array"].index(attr['type']),
                    key=f"type_{i}"
                )
                attr_required = st.checkbox("Povinný:", attr.get('required', False), key=f"req_{i}")
                attr_description = st.text_input("Popis:", attr.get('description', ''), key=f"desc_{i}")
                
                if st.button("Odstrániť atribút", key=f"del_{i}"):
                    continue
                
                updated_attributes.append({
                    'name': attr_name,
                    'type': attr_type,
                    'required': attr_required,
                    'description': attr_description
                })
        
        # Add new attribute
        with st.expander("Pridať nový atribút"):
            new_attr_name = st.text_input("Názov atribútu:", key="new_attr_name")
            new_attr_type = st.selectbox(
                "Typ atribútu:",
                ["string", "number", "integer", "boolean", "object", "array"],
                key="new_attr_type"
            )
            new_attr_required = st.checkbox("Povinný:", key="new_attr_required")
            new_attr_description = st.text_input("Popis:", key="new_attr_description")
            
            if st.button("Pridať atribút") and new_attr_name:
                updated_attributes.append({
                    'name': new_attr_name,
                    'type': new_attr_type,
                    'required': new_attr_required,
                    'description': new_attr_description
                })
        
        # Save changes
        if st.button("Uložiť zmeny"):
            object_types[selected_key] = {
                'name': new_name,
                'color': new_color,
                'attributes': updated_attributes
            }
            
            save_object_types(object_types)
            st.success(f"Typ '{new_name}' bol úspešne aktualizovaný!")
            st.rerun()

def _render_add_type(object_types):
    """Render the view for adding a new object type."""
    st.header("Pridať nový typ objektu")
    
    # Basic properties
    new_key = st.text_input("Kľúč typu (napr. PERSON, PLACE):")
    new_name = st.text_input("Názov typu:")
    new_color = st.color_picker("Farba:", "#CCCCCC")
    
    # Attributes
    st.subheader("Atribúty")
    
    attributes = []
    num_attrs = st.session_state.get('num_attrs', 1)
    
    for i in range(num_attrs):
        with st.expander(f"Atribút {i+1}", expanded=(i == num_attrs-1)):
            attr_name = st.text_input("Názov atribútu:", key=f"add_name_{i}")
            attr_type = st.selectbox(
                "Typ atribútu:",
                ["string", "number", "integer", "boolean", "object", "array"],
                key=f"add_type_{i}"
            )
            attr_required = st.checkbox("Povinný:", key=f"add_req_{i}")
            attr_description = st.text_input("Popis:", key=f"add_desc_{i}")
            
            if attr_name:
                attributes.append({
                    'name': attr_name,
                    'type': attr_type,
                    'required': attr_required,
                    'description': attr_description
                })
    
    if st.button("Pridať ďalší atribút"):
        st.session_state.num_attrs = num_attrs + 1
        st.rerun()
    
    # Save new type
    if st.button("Uložiť nový typ"):
        if not new_key or not new_name:
            st.error("Kľúč a názov typu sú povinné!")
        elif new_key in object_types:
            st.error(f"Typ s kľúčom '{new_key}' už existuje!")
        else:
            object_types[new_key] = {
                'name': new_name,
                'color': new_color,
                'attributes': attributes
            }
            
            save_object_types(object_types)
            st.success(f"Nový typ '{new_name}' bol úspešne pridaný!")
            st.session_state.num_attrs = 1
            st.rerun()

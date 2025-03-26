import pandas as pd
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

# Inicializácia closure_table v session_state
if 'closure_table' not in st.session_state:
    st.session_state.closure_table = pd.DataFrame([
        {'ancestor': 'Osoba', 'descendant': 'Osoba', 'depth': 0, 'is_descendant_koko': False},
        {'ancestor': 'Osoba', 'descendant': 'Majetok', 'depth': 1, 'is_descendant_koko': False},
        {'ancestor': 'Majetok', 'descendant': 'Majetok', 'depth': 0, 'is_descendant_koko': False},
    ])

# Implementácia add_node pre Closure Table
def add_node(closure_table, parent, new_node, is_descendant_koko=False):
    new_entries = []

    ancestors = closure_table[closure_table['descendant'] == parent]
    for _, ancestor_row in ancestors.iterrows():
        new_entries.append({
            'ancestor': ancestor_row['ancestor'],
            'descendant': new_node,
            'depth': ancestor_row['depth'] + 1,
            'is_descendant_koko': is_descendant_koko
        })

    new_entries.append({'ancestor': new_node, 'descendant': new_node, 'depth': 0, 'is_descendant_koko': is_descendant_koko})

    return pd.concat([closure_table, pd.DataFrame(new_entries)], ignore_index=True)

# Implementácia move_node pre Closure Table (zachováva existujúci flag)
def move_node(closure_table, node_to_move, new_parent):
    descendants = closure_table[closure_table['ancestor'] == node_to_move]['descendant'].tolist()
    closure_table = closure_table[~((closure_table['descendant'].isin(descendants)) & (closure_table['ancestor'].isin(
        closure_table[closure_table['descendant'] == node_to_move]['ancestor'].tolist()
    )) & (closure_table['ancestor'] != closure_table['descendant']))]

    new_paths = []
    new_ancestors = closure_table[closure_table['descendant'] == new_parent]

    for descendant in descendants:
        descendant_depth = closure_table[(closure_table['ancestor'] == node_to_move) & (closure_table['descendant'] == descendant)]['depth'].iloc[0]
        is_koko = closure_table[closure_table['descendant'] == descendant]['is_descendant_koko'].iloc[0]
        for _, ancestor_row in new_ancestors.iterrows():
            new_paths.append({
                'ancestor': ancestor_row['ancestor'],
                'descendant': descendant,
                'depth': ancestor_row['depth'] + 1 + descendant_depth,
                'is_descendant_koko': is_koko
            })

    closure_table = pd.concat([closure_table, pd.DataFrame(new_paths)], ignore_index=True)
    return closure_table.drop_duplicates()

# Implementácia delete_node pre Closure Table
def delete_node(closure_table, node_to_delete):
    descendants = closure_table[closure_table['ancestor'] == node_to_delete]['descendant'].tolist()
    return closure_table[~closure_table['descendant'].isin(descendants) & ~closure_table['ancestor'].isin(descendants)]

# Sidebar UI
st.sidebar.header("Správa stromu")
action = st.sidebar.selectbox("Akcia:", ["Pridať nový uzol", "Presunúť uzol", "Editovať uzol", "Zmazať uzol"])

if action == "Pridať nový uzol":
    selected_parent = st.sidebar.selectbox("Vyber rodiča:", st.session_state.closure_table['descendant'].unique())
    new_node_name = st.sidebar.text_input("Meno nového uzla:")
    is_descendant_koko = st.sidebar.checkbox("KoKo", value=False)

    if st.sidebar.button("Pridaj nový uzol"):
        if new_node_name.strip():
            st.session_state.closure_table = add_node(st.session_state.closure_table, selected_parent, new_node_name.strip(), is_descendant_koko)
            st.sidebar.success(f"Uzol '{new_node_name}' pridaný pod '{selected_parent}'!")
            st.rerun()
        else:
            st.sidebar.error("Zadaj názov nového uzla!")

elif action == "Presunúť uzol":
    node_to_move = st.sidebar.selectbox("Uzol na presun:", st.session_state.closure_table['descendant'].unique())
    possible_new_parents = st.session_state.closure_table['descendant'].unique().tolist()
    possible_new_parents.remove(node_to_move)
    new_parent = st.sidebar.selectbox("Nový rodič:", possible_new_parents)

    if st.sidebar.button("Presuň uzol"):
        st.session_state.closure_table = move_node(st.session_state.closure_table, node_to_move, new_parent)
        st.sidebar.success(f"Uzol '{node_to_move}' presunutý pod '{new_parent}'!")
        st.rerun()

elif action == "Editovať uzol":
    node_to_edit = st.sidebar.selectbox("Vyber uzol na editáciu:", st.session_state.closure_table['descendant'].unique())
    current_value = st.session_state.closure_table[st.session_state.closure_table['descendant'] == node_to_edit]['is_descendant_koko'].iloc[0]
    new_koko_value = st.sidebar.checkbox("KoKo", value=current_value)

    if st.sidebar.button("Uložiť zmeny"):
        st.session_state.closure_table.loc[st.session_state.closure_table['descendant'] == node_to_edit, 'is_descendant_koko'] = new_koko_value
        st.sidebar.success(f"Uzol '{node_to_edit}' upravený!")
        st.rerun()

elif action == "Zmazať uzol":
    node_to_delete = st.sidebar.selectbox("Vyber uzol na zmazanie:", st.session_state.closure_table['descendant'].unique())
    if st.sidebar.button("Zmaž uzol"):
        st.session_state.closure_table = delete_node(st.session_state.closure_table, node_to_delete)
        st.sidebar.success(f"Uzol '{node_to_delete}' a jeho potomkovia boli zmazaní!")
        st.rerun()

# Dynamické vytváranie grafu
unique_nodes = st.session_state.closure_table[['descendant', 'is_descendant_koko']].drop_duplicates()
nodes = [Node(id=row['descendant'], label=row['descendant'], color="red" if row['is_descendant_koko'] else "#97C2FC") for _, row in unique_nodes.iterrows()]

direct_edges = st.session_state.closure_table[st.session_state.closure_table['depth'] == 1]
edges = [Edge(source=row['ancestor'], target=row['descendant']) for _, row in direct_edges.iterrows()]

# Konfigurácia grafu
config = Config(width=700, height=500, directed=True, nodeHighlightBehavior=True, highlightColor="#F7A7A6")

# Zobrazenie grafu
st.header("Vizualizácia dátovej mapy")
agraph(nodes=nodes, edges=edges, config=config)

# Checkbox pre zobrazenie closure_table
show_table = st.checkbox("Zobraziť closure_table", value=st.session_state.get('show_table', False))
st.session_state.show_table = show_table

if show_table:
    st.dataframe(st.session_state.closure_table)
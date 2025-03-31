import pandas as pd
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config
import hashlib

# Výber režimu zobrazenia
page = st.sidebar.radio("Režim:", ["Administrátor", "Používateľ"])

# Compute a unique file identifier
def get_file_id(uploaded_file):
    return hashlib.md5(f"{uploaded_file.name}{uploaded_file.size}".encode()).hexdigest()

if 'processed_file_ids' not in st.session_state:
    st.session_state.processed_file_ids = set()

uploaded_file = st.sidebar.file_uploader("Nahraj admin closure_table (CSV)", type="csv")
if uploaded_file is not None:
    file_id = get_file_id(uploaded_file)
    if file_id not in st.session_state.processed_file_ids:
        df = pd.read_csv(uploaded_file)
        st.session_state.admin_closure_table = df
        st.session_state.working_file_id = file_id
        st.session_state.processed_file_ids = {file_id}
        st.rerun()

if 'admin_closure_table' not in st.session_state:
    st.session_state.admin_closure_table = pd.DataFrame([
        {'ancestor': 'Zem', 'descendant': 'Zem', 'depth': 0, 'is_descendant_koko': True, 'is_user_defined': False},
        {'ancestor': 'Zem', 'descendant': 'Živé', 'depth': 1, 'is_descendant_koko': True, 'is_user_defined': False},
        {'ancestor': 'Živé', 'descendant': 'Živé', 'depth': 0, 'is_descendant_koko': True, 'is_user_defined': False},
    ])

if 'user_closure_table' not in st.session_state:
    st.session_state.user_closure_table = pd.DataFrame(columns=['ancestor', 'descendant', 'depth', 'is_descendant_koko', 'is_user_defined'])

@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

admin_csv = convert_df_to_csv(st.session_state.admin_closure_table)
st.sidebar.download_button(
    label="Stiahnuť admin closure_table ako CSV",
    data=admin_csv,
    file_name='admin_closure_table.csv',
    mime='text/csv'
)

def add_node(closure_table, parent, new_node, is_descendant_koko=False, is_user_defined=True):
    new_entries = []
    ancestors = closure_table[closure_table['descendant'] == parent]
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
    return pd.concat([closure_table, pd.DataFrame(new_entries)], ignore_index=True)

def delete_node(closure_table, node_to_delete):
    descendants = closure_table[closure_table['ancestor'] == node_to_delete]['descendant'].tolist()
    return closure_table[~closure_table['descendant'].isin(descendants) & ~closure_table['ancestor'].isin(descendants)]

def move_node(closure_table, node_to_move, new_parent):
    is_root = closure_table[(closure_table['ancestor'] == node_to_move) & (closure_table['depth'] == 0)].shape[0] == 1
    has_no_ancestors = closure_table[(closure_table['descendant'] == node_to_move) & (closure_table['depth'] > 0)].empty
    if is_root and has_no_ancestors:
        st.error(f"Uzol '{node_to_move}' je root uzol a nemôže byť presunutý.")
        return closure_table

    descendants_of_node = closure_table[closure_table['ancestor'] == node_to_move]['descendant'].tolist()
    if new_parent in descendants_of_node:
        st.error(f"Uzol '{node_to_move}' nemôže byť presunutý pod svojho potomka '{new_parent}'!")
        return closure_table

    subtree = closure_table[closure_table['ancestor'] == node_to_move].copy()
    subtree_descendants = subtree['descendant'].unique().tolist()
    ancestors = closure_table[closure_table['descendant'] == node_to_move]['ancestor'].unique().tolist()

    closure_table = closure_table[~(
        closure_table['ancestor'].isin(ancestors) &
        closure_table['descendant'].isin(subtree_descendants) &
        (closure_table['ancestor'] != closure_table['descendant'])
    )]

    new_ancestors = closure_table[closure_table['descendant'] == new_parent].copy()

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
    closure_table = pd.concat([closure_table, pd.DataFrame(new_paths)], ignore_index=True)
    return closure_table.drop_duplicates()

# === ADMINISTRÁTOR STRÁNKA ===
if page == "Administrátor":
    st.sidebar.header("Správa stromu")
    action = st.sidebar.selectbox("Akcia:", ["Pridať nový uzol", "Zmazať uzol", "Presunúť uzol"])

    if action == "Pridať nový uzol":
        selected_parent = st.sidebar.selectbox("Vyber rodiča:", st.session_state.admin_closure_table['descendant'].unique())
        new_node_name = st.sidebar.text_input("Meno nového uzla:")

        if st.sidebar.button("Pridaj nový uzol"):
            if new_node_name.strip():
                st.session_state.admin_closure_table = add_node(
                    st.session_state.admin_closure_table,
                    selected_parent,
                    new_node_name.strip(),
                    is_descendant_koko=True,
                    is_user_defined=False
                )
                st.sidebar.success(f"Uzol '{new_node_name}' pridaný pod '{selected_parent}'!")
                st.rerun()
            else:
                st.sidebar.error("Zadaj názov nového uzla!")

    elif action == "Zmazať uzol":
        node_to_delete = st.sidebar.selectbox("Vyber uzol na zmazanie:", st.session_state.admin_closure_table['descendant'].unique())
        if st.sidebar.button("Zmaž uzol"):
            st.session_state.admin_closure_table = delete_node(st.session_state.admin_closure_table, node_to_delete)
            st.sidebar.success(f"Uzol '{node_to_delete}' a jeho potomkovia boli zmazaní!")
            st.rerun()

    elif action == "Presunúť uzol":
        node_to_move = st.sidebar.selectbox("Vyber uzol na presun:", st.session_state.admin_closure_table['descendant'].unique())
        possible_parents = st.session_state.admin_closure_table['descendant'].unique().tolist()
        possible_parents.remove(node_to_move)
        new_parent = st.sidebar.selectbox("Vyber nový rodič:", possible_parents)

        if st.sidebar.button("Presuň uzol"):
            st.session_state.admin_closure_table = move_node(st.session_state.admin_closure_table, node_to_move, new_parent)
            st.rerun()

    admin_table = st.session_state.admin_closure_table.copy()
    unique_nodes = admin_table[['descendant', 'is_descendant_koko']].drop_duplicates()
    nodes = [Node(id=row['descendant'], label=row['descendant'], color="red" if row['is_descendant_koko'] else "#97C2FC") for _, row in unique_nodes.iterrows()]
    direct_edges = admin_table[admin_table['depth'] == 1]
    edges = [Edge(source=row['ancestor'], target=row['descendant']) for _, row in direct_edges.iterrows()]
    config = Config(width=700, height=500, directed=True, nodeHighlightBehavior=True, highlightColor="#F7A7A6")
    st.header("Vizualizácia dátovej mapy (admin)")
    agraph(nodes=nodes, edges=edges, config=config)

elif page == "Používateľ":
    def compute_completion_score(df):
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

    st.sidebar.header("Moje uzly")
    st.sidebar.header("Pridaj svoj uzol")
    admin_nodes = st.session_state.admin_closure_table['descendant'].unique()
    user_defined_nodes = st.session_state.user_closure_table[st.session_state.user_closure_table['is_user_defined'] == True]['descendant'].unique()
    valid_parents = [node for node in admin_nodes if node not in user_defined_nodes]

    if valid_parents:
        selected_parent = st.sidebar.selectbox("Vyber rodiča:", valid_parents)
        new_node_name = st.sidebar.text_input("Názov môjho uzla:")
        if st.sidebar.button("Pridať môj uzol"):
            if new_node_name.strip():
                merged_table = pd.concat([st.session_state.admin_closure_table, st.session_state.user_closure_table])
                st.session_state.user_closure_table = add_node(
                    merged_table,
                    selected_parent,
                    new_node_name.strip(),
                    is_descendant_koko=False,
                    is_user_defined=True
                )
                st.sidebar.success(f"Tvoj uzol '{new_node_name}' bol pridaný pod '{selected_parent}'!")
                st.rerun()
            else:
                st.sidebar.error("Zadaj názov svojho uzla!")
    else:
        st.sidebar.info("Nie sú dostupní žiadni platní rodičia.")

    deletable_nodes = st.session_state.user_closure_table[st.session_state.user_closure_table['is_user_defined'] == True]['descendant'].unique()
    if len(deletable_nodes) > 0:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Zmaž svoj uzol")
        node_to_delete = st.sidebar.selectbox("Vyber uzol na zmazanie:", deletable_nodes)
        if st.sidebar.button("Zmaž môj uzol"):
            st.session_state.user_closure_table = delete_node(st.session_state.user_closure_table, node_to_delete)
            st.sidebar.success(f"Uzol '{node_to_delete}' bol zmazaný.")
            st.rerun()

    combined_table = pd.concat([st.session_state.admin_closure_table, st.session_state.user_closure_table]).drop_duplicates()

    # Postavíme strom len z väzieb depth == 1
    def build_tree(df):
        tree = {}
        children_set = set()

        for _, row in df[df['depth'] == 1].iterrows():
            parent, child = row['ancestor'], row['descendant']
            tree.setdefault(parent, []).append(child)
            children_set.add(child)

        return tree, children_set

    def render_tree_sorted(tree, node, level=0, visited=None):
        if visited is None:
            visited = set()

        if node in visited:
            return
        visited.add(node)

        children = sorted(tree.get(node, []))
        indent = " " * level
        icon = "📁" if children else "📄"
        st.markdown(f"{indent}{icon} {node}")

        for child in children:
            render_tree_sorted(tree, child, level + 1, visited)
    
    full_tree, children_set = build_tree(combined_table)

    from streamlit_tree_select import tree_select

    def build_tree_data(df):
        """Rekurzívne premení closure table na formát pre streamlit_tree_select"""
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

        # Zisti rooty: tie, ktoré nie sú potomkom žiadneho iného uzla
        all_nodes = set(df['descendant'].unique())
        child_nodes = set(df[df['depth'] == 1]['descendant'].unique())
        roots = list(all_nodes - child_nodes)

        return [build_subtree(root) for root in sorted(roots)]


    # Root uzly = tie, ktoré nie sú nikde potomkom
    all_nodes = set(combined_table['descendant'].unique())
    root_candidates = [n for n in all_nodes if n not in children_set]

    tree_data = build_tree_data(combined_table)
    st.subheader("🌳 Interaktívna stromová štruktúra")
    selected = tree_select(tree_data)

    if selected:
        st.success(f"Vybraný uzol: {selected}")


    unique_nodes = combined_table[['descendant', 'is_descendant_koko']].drop_duplicates()
    nodes = [Node(id=row['descendant'], label=row['descendant'], color="red" if row['is_descendant_koko'] else "#97C2FC") for _, row in unique_nodes.iterrows()]
    direct_edges = combined_table[combined_table['depth'] == 1]
    edges = [Edge(source=row['ancestor'], target=row['descendant']) for _, row in direct_edges.iterrows()]
    config = Config(width=700, height=500, directed=True, nodeHighlightBehavior=True, highlightColor="#F7A7A6")
    st.header("Vizualizácia dátovej mapy (používateľ)")
    agraph(nodes=nodes, edges=edges, config=config)

    total, completed = compute_completion_score(combined_table)
    st.markdown(f"### Skóre vyplnenosti stromu: {completed} / {total} koncových KoKo uzlov má potomkov")

show_table = st.checkbox("Zobraziť closure_table", value=st.session_state.get('show_table', False))
st.session_state.show_table = show_table

if show_table:
    st.subheader("Admin closure table")
    st.dataframe(st.session_state.admin_closure_table)
    st.subheader("Používateľská closure table")
    st.dataframe(st.session_state.user_closure_table)
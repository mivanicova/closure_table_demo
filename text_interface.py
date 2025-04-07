import json
import os
import re
import uuid
from models import ClosureTable
from utils import get_object_type_names, get_object_type_attributes


class TextInterface:
    """Class for managing a natural language interface to build the admin_closure_table."""
    
    def __init__(self, admin_table):
        """Initialize the TextInterface with an admin closure table.
        
        Args:
            admin_table: ClosureTable instance for admin data
        """
        self.admin_table = admin_table
        self.is_configured = False
        self.client = None
        
    def setup_openai_client(self):
        """Set up the OpenAI client with API key from environment or session state."""
        import streamlit as st
        import openai
        
        # Try to get API key from environment variable first
        api_key = os.environ.get("OPENAI_API_KEY")
        
        # If not in environment, try to get from session state
        if not api_key and "openai_api_key" in st.session_state:
            api_key = st.session_state.openai_api_key
            
        # Set the API key for the OpenAI client
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)
            self.is_configured = True
        else:
            self.is_configured = False
            
    def render(self):
        """Render the text interface UI."""
        import streamlit as st
        import openai
        
        # Set up OpenAI client if not already configured
        if not self.is_configured:
            self.setup_openai_client()
            
        st.header("Textové rozhranie pre správu stromu")
        
        # API key input if not configured
        if not self.is_configured:
            st.warning("Pre použitie textového rozhrania je potrebný OpenAI API kľúč.")
            api_key = st.text_input("OpenAI API kľúč:", type="password")
            if api_key:
                st.session_state.openai_api_key = api_key
                self.setup_openai_client()
                st.success("API kľúč bol nastavený!")
                st.rerun()
            return
        
        # Display instructions
        with st.expander("Inštrukcie", expanded=False):
            st.markdown("""
            ### Ako používať textové rozhranie
            
            Toto rozhranie vám umožňuje spravovať strom pomocou prirodzeného jazyka. Môžete zadávať príkazy ako:
            
            - "Pridaj nový uzol 'Mačka' pod 'Živé'"
            - "Vytvor uzol 'Škola' typu 'Miesto' pod 'Zem'"
            - "Presuň uzol 'Pes' pod 'Domáce zvieratá'"
            - "Zmaž uzol 'Starý počítač'"
            - "Pridaj uzol 'Jablko' typu 'Neživý fyzický objekt' s atribútmi: Typ='potravina', Hmotnosť=0.2"
            
            Systém sa pokúsi porozumieť vašim príkazom a vykonať požadované operácie.
            """)
        
        # Text input for natural language commands
        user_input = st.text_area("Zadajte príkaz v prirodzenom jazyku:", height=100)
        
        if st.button("Vykonať príkaz"):
            if user_input.strip():
                with st.spinner("Spracovávam príkaz..."):
                    result = self.process_command(user_input)
                    if result["success"]:
                        st.success(result["message"])
                        # Rerun the app to update the visualization
                        st.rerun()
                    else:
                        st.error(result["message"])
            else:
                st.warning("Zadajte príkaz.")
                
        # Show conversation history
        if "conversation_history" in st.session_state:
            with st.expander("História konverzácie", expanded=False):
                for entry in st.session_state.conversation_history:
                    st.markdown(f"**Vy:** {entry['user']}")
                    st.markdown(f"**Systém:** {entry['system']}")
                    st.markdown("---")
    
    def process_command(self, command):
        """Process a natural language command and perform the corresponding operation.
        
        Args:
            command: Natural language command string
            
        Returns:
            dict: Result with success flag and message
        """
        import streamlit as st
        import openai
        
        # Initialize conversation history if it doesn't exist
        if "conversation_history" not in st.session_state:
            st.session_state.conversation_history = []
            
        try:
            # Get all available nodes and node types for context
            all_nodes = list(self.admin_table.get_all_nodes())
            node_types = get_object_type_names()
            
            # Prepare context for the model
            context = {
                "available_nodes": all_nodes,
                "node_types": node_types,
                "current_structure": self._get_tree_structure()
            }
            
            # Call OpenAI API to parse the command with a timeout
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": self._get_system_prompt(context)},
                        {"role": "user", "content": command}
                    ],
                    response_format={"type": "json_object"},
                    timeout=30  # 30 seconds timeout
                )
            except Exception as e:
                # Fallback to a simpler parsing approach if API call fails
                st.warning(f"OpenAI API call failed: {str(e)}. Using fallback parsing method.")
                return self._fallback_parse_command(command, context)
            
            # Parse the response
            parsed_command = json.loads(response.choices[0].message.content)
            
            # Execute the command based on the operation type
            result = self._execute_parsed_command(parsed_command)
            
            # Add to conversation history
            st.session_state.conversation_history.append({
                "user": command,
                "system": result["message"]
            })
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Chyba pri spracovaní príkazu: {str(e)}"
            }
    
    def _get_system_prompt(self, context):
        """Generate the system prompt for the OpenAI model.
        
        Args:
            context: Dictionary with context information
            
        Returns:
            str: System prompt
        """
        return f"""
        You are an AI assistant that helps users manage a hierarchical tree structure using natural language commands.
        
        The tree structure is represented as a closure table with nodes and parent-child relationships.
        
        Available nodes in the tree: {context['available_nodes']}
        
        Available node types: {context['node_types']}
        
        Current tree structure:
        {context['current_structure']}
        
        Your task is to parse natural language commands and convert them to structured operations.
        
        The possible operations are:
        1. add_node - Add a new node to the tree
        2. delete_node - Delete a node from the tree
        3. move_node - Move a node to a new parent
        
        For each command, you should identify:
        - The operation type
        - The node name
        - The parent node name (for add_node and move_node)
        - The node type (for add_node, optional)
        - Attributes (for add_node, optional)
        
        Respond with a JSON object in the following format:
        {{
            "operation": "add_node|delete_node|move_node",
            "node": "node_name",
            "parent": "parent_node_name",  // Only for add_node and move_node
            "node_type": "node_type_name",  // Only for add_node, optional
            "attributes": {{  // Only for add_node, optional
                "attribute_name": "attribute_value",
                ...
            }}
        }}
        
        If you cannot parse the command, respond with:
        {{
            "operation": "unknown",
            "error": "Error message explaining the issue"
        }}
        """
    
    def _get_tree_structure(self):
        """Get a string representation of the current tree structure.
        
        Returns:
            str: String representation of the tree
        """
        df = self.admin_table.to_dataframe()
        direct_edges = df[df['depth'] == 1]
        
        tree_str = ""
        for _, row in direct_edges.iterrows():
            tree_str += f"{row['ancestor']} -> {row['descendant']}\n"
            
        return tree_str
    
    def _fallback_parse_command(self, command, context):
        """Fallback method to parse commands using regex patterns when API call fails.
        
        Args:
            command: Natural language command string
            context: Dictionary with context information
            
        Returns:
            dict: Result with success flag and message
        """
        import streamlit as st
        command = command.lower().strip()
        
        # Pattern for adding a node
        add_pattern = r'(pridaj|vytvor|add|create).*[\'"]([^\'"]+)[\'"].*pod.*[\'"]([^\'"]+)[\'"]'
        add_match = re.search(add_pattern, command)
        
        if add_match:
            node = add_match.group(2).strip()
            parent = add_match.group(3).strip()
            
            # Try to extract node type
            node_type = None
            type_pattern = r'typu?.*[\'"]([^\'"]+)[\'"]'
            type_match = re.search(type_pattern, command)
            if type_match:
                node_type = type_match.group(1).strip()
                # Check if the extracted type is in the available types
                if node_type not in context['node_types']:
                    node_type = None
            
            # Try to extract attributes (simplified)
            attributes = {}
            attr_pattern = r'atrib[uú]t.*?:\s*([^,]+)'
            attr_matches = re.findall(attr_pattern, command)
            for attr_match in attr_matches:
                parts = attr_match.split('=')
                if len(parts) == 2:
                    key = parts[0].strip().strip('\'"')
                    value = parts[1].strip().strip('\'"')
                    attributes[key] = value
            
            return self._execute_parsed_command({
                "operation": "add_node",
                "node": node,
                "parent": parent,
                "node_type": node_type,
                "attributes": attributes
            })
        
        # Pattern for deleting a node
        delete_pattern = r'(zma[zž]|delete|remove).*[\'"]([^\'"]+)[\'"]'
        delete_match = re.search(delete_pattern, command)
        
        if delete_match:
            node = delete_match.group(2).strip()
            return self._execute_parsed_command({
                "operation": "delete_node",
                "node": node
            })
        
        # Pattern for moving a node
        move_pattern = r'(presu[nň]|move).*[\'"]([^\'"]+)[\'"].*pod.*[\'"]([^\'"]+)[\'"]'
        move_match = re.search(move_pattern, command)
        
        if move_match:
            node = move_match.group(2).strip()
            parent = move_match.group(3).strip()
            return self._execute_parsed_command({
                "operation": "move_node",
                "node": node,
                "parent": parent
            })
        
        # If no pattern matches, return unknown operation
        return {
            "success": False,
            "message": "Nepodarilo sa rozpoznať príkaz. Skúste ho preformulovať."
        }
    
    def _execute_parsed_command(self, parsed_command):
        """Execute a parsed command on the admin_closure_table.
        
        Args:
            parsed_command: Dictionary with parsed command information
            
        Returns:
            dict: Result with success flag and message
        """
        import streamlit as st
        operation = parsed_command.get("operation")
        
        if operation == "unknown":
            return {
                "success": False,
                "message": f"Nepodarilo sa spracovať príkaz: {parsed_command.get('error', 'Neznáma chyba')}"
            }
        
        elif operation == "add_node":
            node = parsed_command.get("node")
            parent = parsed_command.get("parent")
            node_type = parsed_command.get("node_type")
            attributes = parsed_command.get("attributes", {})
            
            # Validate required parameters
            if not node or not parent:
                return {
                    "success": False,
                    "message": "Pre pridanie uzla je potrebné zadať názov uzla a rodiča."
                }
                
            # Check if parent exists
            if parent not in self.admin_table.get_all_nodes():
                return {
                    "success": False,
                    "message": f"Rodičovský uzol '{parent}' neexistuje."
                }
                
            # Check if node already exists
            if node in self.admin_table.get_all_nodes():
                return {
                    "success": False,
                    "message": f"Uzol '{node}' už existuje."
                }
                
            # Add UUID to attributes
            attributes['uuid'] = str(uuid.uuid4())
            
            # Add the node
            self.admin_table.add_node(
                parent,
                node,
                is_descendant_koko=True,
                is_user_defined=False,
                node_type=node_type,
                attributes=attributes
            )
            
            # Synchronize user table with admin table
            if 'user_closure_table' in st.session_state:
                st.session_state.user_closure_table = st.session_state.user_closure_table.synchronize_with(self.admin_table)
            
            return {
                "success": True,
                "message": f"Uzol '{node}'{' typu ' + node_type if node_type else ''} bol pridaný pod '{parent}'."
            }
            
        elif operation == "delete_node":
            node = parsed_command.get("node")
            
            # Validate required parameters
            if not node:
                return {
                    "success": False,
                    "message": "Pre zmazanie uzla je potrebné zadať názov uzla."
                }
                
            # Check if node exists
            if node not in self.admin_table.get_all_nodes():
                return {
                    "success": False,
                    "message": f"Uzol '{node}' neexistuje."
                }
                
            # Delete the node
            self.admin_table.delete_node(node)
            
            # Synchronize user table with admin table
            if 'user_closure_table' in st.session_state:
                st.session_state.user_closure_table = st.session_state.user_closure_table.synchronize_with(self.admin_table)
            
            return {
                "success": True,
                "message": f"Uzol '{node}' a jeho potomkovia boli zmazaní."
            }
            
        elif operation == "move_node":
            node = parsed_command.get("node")
            parent = parsed_command.get("parent")
            
            # Validate required parameters
            if not node or not parent:
                return {
                    "success": False,
                    "message": "Pre presun uzla je potrebné zadať názov uzla a nového rodiča."
                }
                
            # Check if node exists
            if node not in self.admin_table.get_all_nodes():
                return {
                    "success": False,
                    "message": f"Uzol '{node}' neexistuje."
                }
                
            # Check if parent exists
            if parent not in self.admin_table.get_all_nodes():
                return {
                    "success": False,
                    "message": f"Rodičovský uzol '{parent}' neexistuje."
                }
                
            try:
                # Move the node
                self.admin_table.move_node(node, parent)
                
                # Synchronize user table with admin table
                if 'user_closure_table' in st.session_state:
                    st.session_state.user_closure_table = st.session_state.user_closure_table.synchronize_with(self.admin_table)
                
                return {
                    "success": True,
                    "message": f"Uzol '{node}' bol presunutý pod '{parent}'."
                }
            except ValueError as e:
                return {
                    "success": False,
                    "message": str(e)
                }
        
        else:
            return {
                "success": False,
                "message": f"Neznáma operácia: {operation}"
            }

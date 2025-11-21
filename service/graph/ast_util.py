

# Utility functions from original file (kept for context)
def make_nid(file_path, node):
    if node is None:
        return None
    # Use start/end *point* (line:column) for better uniqueness and readability,
    # though byte offsets are used here for simplicity as in the original.
    return f"{file_path}:{node.start_byte}:{node.end_byte}"

def get_text(node, source):
    if node is None:
        return None
    return source[node.start_byte:node.end_byte].decode(errors="ignore")

def extract_semantics(node, source):
    """
    Universal semantic extractor for various languages (JS/TS, Java, Python).
    Updated to cover more control flow and literal types for CFG/DFG.
    """
    if node is None:
        return {"semantic_type": None}

    t = node.type

    # helper to safely get text
    def node_text(n):
        try:
            if n is None:
                return None
            return source[n.start_byte:n.end_byte].decode(errors="ignore")
        except Exception:
            return None

    # --------------------------
    # FUNCTION / METHOD
    # --------------------------
    if t in (
        "method_declaration", "constructor_declaration",
        "function_declaration", "function_definition",
        "function", "function_expression", "arrow_function",
        "method_definition", "generator_function",
        "lambda_expression", "lambda"
    ):
        name_node = None
        for c in node.children:
            if c.type in ("identifier", "name", "simple_identifier"):
                name_node = c
                break

        name = node_text(name_node)

        # Gather parameter texts
        params = []
        for c in node.children:
            if c.type in ("formal_parameters", "parameters", "parameter_list"):
                # Collect identifiers under this subtree
                for p in c.children:
                    # Generic parameter types
                    if p.type in ("identifier", "parameter", "typed_parameter", "assignment_pattern", "required_parameter"):
                        ptxt = node_text(p)
                        if ptxt:
                            params.append(ptxt)
                break

        return {
            "semantic_type": "function",
            "name": name,
            "params": params,
            "signature": f"{name}({', '.join(params)})"
        }

    # --------------------------
    # CLASS / TYPE
    # --------------------------
    if t in ("class_declaration", "class_definition", "class", "interface_declaration", "type_alias"):
        name_node = None
        for c in node.children:
            if c.type in ("identifier", "name", "simple_identifier"):
                name_node = c
                break
        return {
            "semantic_type": "class_or_type",
            "name": node_text(name_node)
        }

    # --------------------------
    # VARIABLE DECLARATION / INITIALIZATION
    # --------------------------
    # Python: assignment target is often an 'identifier' child of an 'assignment'
    if t in ("variable_declarator", "variable_declaration", "let_declaration", "const_declaration", "var_declaration"):
        # We try to find the variable's name (the identifier being declared)
        name_node = None
        for c in node.children:
            if c.type in ("identifier", "name", "simple_identifier"):
                name_node = c
                break

        return {
            "semantic_type": "variable_declaration",
            "name": node_text(name_node)
        }

    # --------------------------
    # ASSIGNMENT / UPDATE
    # --------------------------
    if t in ("assignment_expression", "assignment", "update_expression", "augmented_assignment"):
        # For assignment, we need the *target* of the write for DFG
        target_node = node.children[0] if node.child_count > 0 else None
        target_name = node_text(target_node)

        return {
            "semantic_type": "assignment",
            "target_name": target_name # Target of the write operation
        }

    # --------------------------
    # CALL / INVOCATION
    # --------------------------
    if t in ("method_invocation", "call_expression", "call", "invoke_expression", "function_call", "new_expression"):
        # Logic to find function_name/qualified_name remains largely the same
        # ... (simplified for brevity, using original logic)

        # Try to extract a simple identifier or a member expression
        function_name = None
        qualified_name = None

        # Look for the immediate identifier/name child if present
        for c in node.children:
            if c.type in ("identifier", "name", "simple_identifier"):
                function_name = node_text(c)
                break

        if function_name is None:
            # search subtree for member-like node
            def find_member_or_identifier(n):
                if n is None:
                    return None
                if n.type in ("member_expression", "field_access", "attribute", "property_access", "dot_member_expression", "identifier", "name"):
                    return n
                # Only check first few children to limit recursion depth/time
                for ch in n.children[:3]:
                    res = find_member_or_identifier(ch)
                    if res:
                        return res
                return None

            member = find_member_or_identifier(node)
            if member:
                txt = node_text(member)
                qualified_name = txt
                # extract last segment after dot as simple name
                if txt:
                    function_name = txt.split(".")[-1]
                if function_name is None and member.type in ("identifier", "name"):
                    function_name = txt


        return {
            "semantic_type": "call",
            "function_name": function_name,
            "qualified_name": qualified_name
        }

    # --------------------------
    # IDENTIFIER (Read/Use)
    # --------------------------
    if t in ("identifier", "name", "simple_identifier", "shorthand_property_identifier"):
        # This is a general use/read of a variable name
        return {
            "semantic_type": "identifier_use",
            "name": node_text(node)
        }

    # --------------------------
    # RETURN
    # --------------------------
    if t in ("return_statement", "return"):
        return {"semantic_type": "return_statement"}

    # --------------------------
    # CONTROL FLOW STATEMENTS (CFG)
    # --------------------------
    if t in ("if_statement", "for_statement", "while_statement", "do_statement", "switch_statement", "break_statement", "continue_statement"):
        return {"semantic_type": "control_flow_statement"}

    # --------------------------
    # EXCEPTION HANDLING (CFG)
    # --------------------------
    if t in ("try_statement", "catch_clause", "throw_statement", "finally_clause"):
        return {"semantic_type": "exception_handling"}

    # --------------------------
    # IMPORT / USE (Cross-File)
    # --------------------------
    if t in ("import_statement", "use_declaration", "namespace_import", "import_declaration"):
        # For DFG/Call Graph resolution outside the file
        return {"semantic_type": "import_statement"}

    # --------------------------
    # LITERALS (DFG)
    # --------------------------
    if t in ("string_literal", "number_literal", "true", "false", "null", "integer", "float", "list_literal", "object_literal"):
        return {
            "semantic_type": "literal",
            "value": node_text(node)
        }


    # Default
    return {"semantic_type": None}
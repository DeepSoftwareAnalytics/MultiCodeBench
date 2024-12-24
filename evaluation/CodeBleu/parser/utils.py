import re
from io import StringIO
import  tokenize
import ast
from tree_sitter import Language, Parser



def remove_comments_and_docstrings_python(source, LANGUAGE, debug=False):
    def print_ast(node, level=0):
        if debug:
            print('  ' * level + f'{node.type} [start: {node.start_point}, end: {node.end_point}]')
        
        for child in node.children:
            print_ast(child, level + 1)
    
    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))
    root_node = tree.root_node

    if debug:
        print_ast(root_node)

    comments_and_docstrings = []
    errors = []

    first_code_start = None
    last_code_end = 0

    def traverse(node, parent_type=None):
        nonlocal first_code_start, last_code_end

        if node.type == 'comment':
            comments_and_docstrings.append((node.start_point, node.end_point))

        if node.type == 'string' and parent_type in ('function_definition', 'class_definition', 'module'):
            comments_and_docstrings.append((node.start_point, node.end_point))

        if node.type == 'expression_statement':
            if node.children:
                child = node.children[0]
                if child.type == 'string':
                    comments_and_docstrings.append((child.start_point, child.end_point))

        if node.type not in ('comment', 'string'):
            if first_code_start is None:  
                first_code_start = node.start_point[0]  
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child, node.type)

    traverse(root_node)

    all_removals = comments_and_docstrings + errors
    all_removals.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)
    total_lines = len(cleaned_source)

    for (start_point, end_point) in all_removals:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if start_line >= total_lines or end_line >= total_lines:
            continue  

        if start_line == end_line:
            cleaned_source[start_line] = (
                cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
            )
        else:
            cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

            for i in range(start_line + 1, min(end_line, total_lines - 1)):
                cleaned_source[i] = ' ' * len(cleaned_source[i])

            if end_line < total_lines:
                cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None and last_code_end < total_lines:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source


def remove_comments_and_docstrings_javascript(source, LANGUAGE):

    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))
    
    root_node = tree.root_node
    comments_and_errors = []
    first_code_start = None
    last_code_end = 0

    def traverse(node):
        nonlocal first_code_start, last_code_end
        if node.type in ('comment', 'html_comment'):
            comments_and_errors.append((node.start_point, node.end_point, 'comment'))

        if node.type not in ('comment', 'html_comment'):
            if first_code_start is None:
                first_code_start = node.start_point[0]  
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child)

    traverse(root_node)

    comments_and_errors.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)

    lines_to_remove = set()
    for (start_point, end_point, node_type) in comments_and_errors:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if node_type == 'comment':
            if start_line == end_line:
                cleaned_source[start_line] = (
                    cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
                )
            else:
                cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

                for i in range(start_line + 1, end_line):
                    cleaned_source[i] = ' ' * len(cleaned_source[i])

                cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = [line for i, line in enumerate(cleaned_source) if i not in lines_to_remove]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source

def remove_comments_and_docstrings_typescript(source, LANGUAGE):

    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))
    
    root_node = tree.root_node
    comments_and_errors = []
    first_code_start = None
    last_code_end = 0

    def traverse(node):
        nonlocal first_code_start, last_code_end

        if node.type in ('comment', 'html_comment'):
            comments_and_errors.append((node.start_point, node.end_point, 'comment'))

        if node.type not in ('comment', 'html_comment'):
            if first_code_start is None:
                first_code_start = node.start_point[0]  
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child)

    traverse(root_node)

    comments_and_errors.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)

    lines_to_remove = set()
    for (start_point, end_point, node_type) in comments_and_errors:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if node_type == 'comment':
            if start_line == end_line:
                cleaned_source[start_line] = (
                    cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
                )
            else:
                cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

                for i in range(start_line + 1, end_line):
                    cleaned_source[i] = ' ' * len(cleaned_source[i])

                cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = [line for i, line in enumerate(cleaned_source) if i not in lines_to_remove]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source

def remove_comments_and_docstrings_solidity(source, LANGUAGE):

    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))

    root_node = tree.root_node

    comments_and_docstrings = []

    first_code_start = None
    last_code_end = 0

    def traverse(node, previous_node=None):
        nonlocal first_code_start, last_code_end

        if node.type == 'comment':
            comments_and_docstrings.append((node.start_point, node.end_point))
        
        if node.type == 'string_literal' and previous_node and previous_node.type in ('function_definition', 'contract_definition', 'library_definition'):
            comments_and_docstrings.append((node.start_point, node.end_point))

        if node.type not in ('comment', 'string_literal'):
            if first_code_start is None:
                first_code_start = node.start_point[0] 
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child, node)

    traverse(root_node)

    comments_and_docstrings.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)  
    source_line_count = len(cleaned_source)  

    for (start_point, end_point) in comments_and_docstrings:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if start_line < source_line_count and end_line < source_line_count:
            if start_line == end_line:
                cleaned_source[start_line] = (
                    cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
                )
            else:
                cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

                for i in range(start_line + 1, end_line):
                    if i < source_line_count:
                        cleaned_source[i] = ' ' * len(cleaned_source[i])

                cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source



def remove_comments_and_docstrings_go(source, LANGUAGE):
    lines = source.splitlines(True)
    cleaned_lines = [line if not (line.lstrip() and line.lstrip()[0] == '#') else '\n' for line in lines]
    source = ''.join(cleaned_lines)

    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))

    root_node = tree.root_node

    comments_and_docstrings = []
    error_lines = set()  

    first_code_start = None
    last_code_end = 0

    def traverse(node, previous_node=None):
        nonlocal first_code_start, last_code_end

        if node.type == 'comment':
            comments_and_docstrings.append((node.start_point, node.end_point))


        if node.type not in ('comment', 'string_literal'):
            if first_code_start is None:
                first_code_start = node.start_point[0]  
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child, node)

    traverse(root_node)

    comments_and_docstrings.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)  
    source_line_count = len(cleaned_source)

    for (start_point, end_point) in comments_and_docstrings:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if start_line < source_line_count and end_line < source_line_count:
            if start_line == end_line:
                cleaned_source[start_line] = (
                    cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
                )
            else:
                cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

                for i in range(start_line + 1, end_line):
                    if i < source_line_count:
                        cleaned_source[i] = ' ' * len(cleaned_source[i])

                cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = [line if i not in error_lines else '\n' for i, line in enumerate(cleaned_source)]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None and last_code_end < source_line_count:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source


def remove_comments_and_docstrings_csharp(source, LANGUAGE):
    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))

    root_node = tree.root_node

    comments_and_docstrings = []

    first_code_start = None
    last_code_end = 0

    def traverse(node):
        nonlocal first_code_start, last_code_end

        if node.type == 'comment':
            comment_text = source[node.start_byte:node.end_byte]
            if comment_text.strip().startswith("///"):
                comments_and_docstrings.append((node.start_point, node.end_point, 'docstring'))
            else:
                comments_and_docstrings.append((node.start_point, node.end_point, 'comment'))

        if node.type not in ('comment'):
            if first_code_start is None:
                first_code_start = node.start_point[0] 
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child)

    traverse(root_node)

    comments_and_docstrings.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)  

    lines_to_remove = set() 

    for (start_point, end_point, node_type) in comments_and_docstrings:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if start_line == end_line:
            cleaned_source[start_line] = (
                cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
            )
        else:
            cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

            for i in range(start_line + 1, end_line):
                cleaned_source[i] = ' ' * len(cleaned_source[i])

            cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = [line for i, line in enumerate(cleaned_source) if i not in lines_to_remove]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)
    return cleaned_source



def remove_comments_and_docstrings_cpp(source, LANGUAGE):
    
    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))
    root_node = tree.root_node
    comments_docstrings_errors = []

    first_code_start = None
    last_code_end = 0

    def traverse(node, parent_type=None):
        nonlocal first_code_start, last_code_end
        if node.type == 'comment':
            comments_docstrings_errors.append((node.start_point, node.end_point, 'comment'))

        if node.type == 'string_literal' and parent_type == 'function_definition':
            comments_docstrings_errors.append((node.start_point, node.end_point, 'string_literal'))

        if node.type not in ('comment', 'string_literal'):  
            if first_code_start is None:
                first_code_start = node.start_point[0] 
            last_code_end = node.end_point[0] 

        for child in node.children:
            traverse(child, node.type)

    traverse(root_node)

    comments_docstrings_errors.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)  

    lines_to_remove = set()
    for (start_point, end_point, node_type) in comments_docstrings_errors:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if node_type == 'comment' or node_type == 'string_literal':
            if start_line == end_line:
                cleaned_source[start_line] = (
                    cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
                )
            else:
                cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

                for i in range(start_line + 1, end_line):
                    cleaned_source[i] = ' ' * len(cleaned_source[i])

                cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = [line for i, line in enumerate(cleaned_source) if i not in lines_to_remove]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source



def remove_comments_and_docstrings_c(source, LANGUAGE):
    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))

    root_node = tree.root_node

    comments_and_docstrings = []

    first_code_start = None
    last_code_end = 0

    def traverse(node, parent_type=None):
        nonlocal first_code_start, last_code_end
        if node.type == 'comment':
            comments_and_docstrings.append((node.start_point, node.end_point, 'comment'))

        if node.type == 'string_literal':
            if parent_type == 'function_definition':
                comments_and_docstrings.append((node.start_point, node.end_point, 'docstring'))
            elif node.prev_sibling and node.prev_sibling.type == 'function_definition':
                comments_and_docstrings.append((node.start_point, node.end_point, 'docstring'))

        if node.type not in ('comment', 'string_literal'):
            if first_code_start is None:
                first_code_start = node.start_point[0]  
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child, node.type)

    traverse(root_node)

    comments_and_docstrings.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)  
    lines_to_remove = set()  

    for (start_point, end_point, node_type) in comments_and_docstrings:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if start_line == end_line:
            cleaned_source[start_line] = (
                cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
            )
        else:
            cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

            for i in range(start_line + 1, end_line):
                cleaned_source[i] = ' ' * len(cleaned_source[i])
            cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = [line for i, line in enumerate(cleaned_source) if i not in lines_to_remove]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source


def remove_comments_and_docstrings_java(source, LANGUAGE):

    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))
    root_node = tree.root_node

    comments_and_docstrings = []

    first_code_start = None
    last_code_end = 0

    def traverse(node, parent_type=None):
        nonlocal first_code_start, last_code_end

        if node.type in ('comment', 'line_comment', 'block_comment'):
            comments_and_docstrings.append((node.start_point, node.end_point, 'comment'))

        if node.type == 'block_comment' and parent_type == 'method_declaration':
            comments_and_docstrings.append((node.start_point, node.end_point, 'docstring'))

        if node.type not in ('comment', 'line_comment', 'block_comment', 'string_literal'):
            if first_code_start is None:
                first_code_start = node.start_point[0] 
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child, node.type)

    traverse(root_node)

    comments_and_docstrings.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)  

    lines_to_remove = set()  

    for (start_point, end_point, node_type) in comments_and_docstrings:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if start_line == end_line:

            cleaned_source[start_line] = (
                cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
            )
        else:
            cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

            for i in range(start_line + 1, end_line):
                cleaned_source[i] = ' ' * len(cleaned_source[i])

            cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = [line for i, line in enumerate(cleaned_source) if i not in lines_to_remove]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)
    return cleaned_source
    

def remove_comments_and_docstrings_rust(source, LANGUAGE):

    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))

    root_node = tree.root_node

    comments_and_docstrings = []

    first_code_start = None
    last_code_end = 0

    def traverse(node, parent_type=None):
        nonlocal first_code_start, last_code_end
        
        if node.type in ('block_comment', 'line_comment', 'doc_comment', 'inner_doc_comment_marker', 'outer_doc_comment_marker'):
            comments_and_docstrings.append((node.start_point, node.end_point))

        if node.type not in ('block_comment', 'line_comment', 'doc_comment', 'inner_doc_comment_marker', 'outer_doc_comment_marker'):
            if first_code_start is None:
                first_code_start = node.start_point[0]  
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child, node.type)

    traverse(root_node)

    comments_and_docstrings.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)  
    source_line_count = len(cleaned_source)  
    
    for (start_point, end_point) in comments_and_docstrings:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if start_line < source_line_count and end_line < source_line_count:
            if start_line == end_line:
                cleaned_source[start_line] = (
                    cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
                )
            else:
                cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

                for i in range(start_line + 1, end_line):
                    if i < source_line_count:
                        cleaned_source[i] = ' ' * len(cleaned_source[i])

                cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)
    return cleaned_source



def remove_comments_and_docstrings_scala(source, LANGUAGE):
    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))
    root_node = tree.root_node

    comments_and_docstrings = []
    lines_to_remove = set()  

    first_code_start = None
    last_code_end = 0

    def traverse(node, parent_type=None):
        nonlocal first_code_start, last_code_end
        if node.type in ('line_comment', 'block_comment', 'comment'):
            comments_and_docstrings.append((node.start_byte, node.end_byte))

        if node.type not in ('comment', 'line_comment', 'block_comment'):
            if first_code_start is None:
                first_code_start = node.start_byte  
            last_code_end = node.end_byte  

        for child in node.children:
            traverse(child, node.type)

    traverse(root_node)

    comments_and_docstrings.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = list(source)
    for start_byte, end_byte in comments_and_docstrings:
        for i in range(start_byte, end_byte):
            cleaned_source[i] = ' ' 

    cleaned_source = ''.join(cleaned_source)

    source_lines = cleaned_source.splitlines(True)
    total_lines = len(source_lines)  

    for i in lines_to_remove:
        if i < total_lines:
            source_lines[i] = '\n'  

    cleaned_source = ''.join(source_lines)

    cleaned_source = re.sub(r'\n\s*(This\s(function|method)[^\n]*)', '', cleaned_source)
    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    if first_code_start is not None and last_code_end > 0:
        cleaned_source = cleaned_source[first_code_start:last_code_end]

    return cleaned_source
    

def remove_comments_and_docstrings_php(source, LANGUAGE):
    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))

    root_node = tree.root_node

    comments_and_docstrings = []

    first_code_start = None
    last_code_end = 0

    def traverse(node, parent_type=None):
        nonlocal first_code_start, last_code_end
        
        if node.type in ('comment', 'line_comment', 'block_comment', 'doc_comment'):
            comments_and_docstrings.append((node.start_point, node.end_point))

        if node.type not in ('comment', 'line_comment', 'block_comment', 'doc_comment'):
            if first_code_start is None:
                first_code_start = node.start_point[0]  
            last_code_end = node.end_point[0] 

        for child in node.children:
            traverse(child, node.type)

    traverse(root_node)

    comments_and_docstrings.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)  
    source_line_count = len(cleaned_source)  

    for (start_point, end_point) in comments_and_docstrings:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if start_line < source_line_count and end_line < source_line_count:
            if start_line == end_line:
                cleaned_source[start_line] = (
                    cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
                )
            else:
                cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

                for i in range(start_line + 1, end_line):
                    if i < source_line_count:
                        cleaned_source[i] = ' ' * len(cleaned_source[i])

                cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source



def remove_comments_and_docstrings_lua(source, LANGUAGE):
    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))

    root_node = tree.root_node

    comments_and_docstrings = []

    first_code_start = None
    last_code_end = 0

    def traverse(node, parent_type=None):
        nonlocal first_code_start, last_code_end
        if node.type == 'comment':
            comments_and_docstrings.append((node.start_point, node.end_point))

        if node.type == 'string' and parent_type == 'function_definition':
            comments_and_docstrings.append((node.start_point, node.end_point))

        if node.type not in ('comment', 'string'):
            if first_code_start is None:
                first_code_start = node.start_point[0]  
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child, node.type)

    traverse(root_node)

    comments_and_docstrings.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)  
    source_line_count = len(cleaned_source)  
    
    for (start_point, end_point) in comments_and_docstrings:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if start_line < source_line_count and end_line < source_line_count:
            if start_line == end_line:
                cleaned_source[start_line] = (
                    cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
                )
            else:
                cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

                for i in range(start_line + 1, end_line):
                    if i < source_line_count:
                        cleaned_source[i] = ' ' * len(cleaned_source[i])

                cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])
    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source



def remove_comments_and_docstrings_kotlin(source, LANGUAGE):

    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))

    root_node = tree.root_node

    comments_and_docstrings = []
    first_code_start = None
    last_code_end = 0

    def traverse(node, parent_type=None):
        nonlocal first_code_start, last_code_end

        if node.type in ('line_comment', 'multiline_comment'):
            comments_and_docstrings.append((node.start_point, node.end_point))

        if node.type == 'string_literal' and parent_type == 'function_declaration':
            comments_and_docstrings.append((node.start_point, node.end_point))

        if node.type not in ('line_comment', 'multiline_comment', 'string_literal'):
            if first_code_start is None:
                first_code_start = node.start_point[0]  
            last_code_end = node.end_point[0]  

        for child in node.children:
            traverse(child, node.type)

    traverse(root_node)

    comments_and_docstrings.sort(reverse=True, key=lambda x: x[0])

    cleaned_source = source.splitlines(True)  
    source_line_count = len(cleaned_source)  

    for (start_point, end_point) in comments_and_docstrings:
        start_line, start_col = start_point
        end_line, end_col = end_point

        if start_line < source_line_count and end_line < source_line_count:
            if start_line == end_line:
                cleaned_source[start_line] = (
                    cleaned_source[start_line][:start_col] + ' ' * (end_col - start_col) + cleaned_source[start_line][end_col:]
                )
            else:
                cleaned_source[start_line] = cleaned_source[start_line][:start_col] + ' ' * (len(cleaned_source[start_line]) - start_col)

                for i in range(start_line + 1, end_line):
                    if i < source_line_count:
                        cleaned_source[i] = ' ' * len(cleaned_source[i])

                cleaned_source[end_line] = ' ' * end_col + cleaned_source[end_line][end_col:]

    cleaned_source = ''.join(cleaned_source)

    if first_code_start is not None:
        cleaned_source = '\n'.join(cleaned_source.splitlines()[first_code_start:last_code_end + 1])

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source




def remove_comments_and_docstrings_swift(source, LANGUAGE):
    parser = Parser()
    parser.set_language(LANGUAGE)
    tree = parser.parse(bytes(source, "utf8"))

    root_node = tree.root_node

    first_code_start = None
    last_code_end = 0

    def traverse(node):
        nonlocal first_code_start, last_code_end
        if node.type != 'comment':
            if first_code_start is None: 
                first_code_start = node.start_byte
            last_code_end = node.end_byte  

        for child in node.children:
            traverse(child)

    traverse(root_node)

    single_line_comment_pattern = r'//.*'
    multi_line_comment_pattern = r'/\*[\s\S]*?\*/'
    doc_comment_pattern = r'///.*'

    def replace_with_whitespace(match):
        return ' ' * (match.end() - match.start())

    cleaned_source = re.sub(doc_comment_pattern, replace_with_whitespace, source)
    cleaned_source = re.sub(multi_line_comment_pattern, replace_with_whitespace, cleaned_source)
    cleaned_source = re.sub(single_line_comment_pattern, replace_with_whitespace, cleaned_source)

    if first_code_start is not None:
        cleaned_source = cleaned_source[first_code_start:last_code_end]

    cleaned_source = re.sub(r'\n\s*\n', '\n', cleaned_source)

    return cleaned_source




def remove_comments_and_docstrings(source,lang):
    LANGUAGE = Language('./build/my-languages.so', lang.lower())
        
    if lang.lower() == "python":
        return remove_comments_and_docstrings_python(source, LANGUAGE)
    elif lang.lower() == "javascript":
        return remove_comments_and_docstrings_javascript(source, LANGUAGE)
    elif lang.lower() == "typescript":
        return remove_comments_and_docstrings_typescript(source, LANGUAGE)
    elif lang.lower() == 'solidity':
        return remove_comments_and_docstrings_solidity(source, LANGUAGE)
    elif lang.lower() == 'go':
        return remove_comments_and_docstrings_go(source, LANGUAGE)
    elif lang.lower() == 'c_sharp':
        return remove_comments_and_docstrings_csharp(source, LANGUAGE)
    elif lang.lower() == 'cpp':
        return remove_comments_and_docstrings_cpp(source, LANGUAGE)
    elif lang.lower() == 'c':
        return remove_comments_and_docstrings_c(source, LANGUAGE)
    elif lang.lower() == 'java':
        return remove_comments_and_docstrings_java(source, LANGUAGE)
    elif lang.lower() == 'rust':
        return remove_comments_and_docstrings_rust(source, LANGUAGE)
    elif lang.lower() == 'scala':
        return remove_comments_and_docstrings_scala(source, LANGUAGE)
    elif lang.lower() == 'php':
        return remove_comments_and_docstrings_php(source, LANGUAGE)
    elif lang.lower() == 'lua':
        return remove_comments_and_docstrings_lua(source, LANGUAGE)
    elif lang.lower() == 'kotlin':
        return remove_comments_and_docstrings_kotlin(source, LANGUAGE)
    elif lang.lower() == 'swift':
        return remove_comments_and_docstrings_swift(source, LANGUAGE)
    else:
        raise ValueError(f"Unsupported language: {lang}")

def tree_to_token_index(root_node):
    if len(root_node.children)==0 and root_node.type not in ['comment', 'ERROR']:
        return [(root_node.start_point,root_node.end_point)]
    else:
        code_tokens=[]
        for child in root_node.children:
            code_tokens+=tree_to_token_index(child)
        return code_tokens
    
    
def index_to_code_token(index,code):
    start_point=index[0]
    end_point=index[1]
    if start_point[0]==end_point[0]:
        s=code[start_point[0]][start_point[1]:end_point[1]]
    else:
        s=""
        s+=code[start_point[0]][start_point[1]:]+ '\n'
        for i in range(start_point[0]+1,end_point[0]):
            s+=code[i]+ '\n'
        s+=code[end_point[0]][:end_point[1]]   
    return s

def get_code_from_node(start, end, index_to_code):
    codes = []
    
    for (s_point, e_point), (idx, code) in index_to_code.items():
        if (s_point >= start and s_point <= end) or (e_point >= start and e_point <= end) or (start >= s_point and end <= e_point):
            codes.append(code)


    return ' '.join(codes)  

def tree_to_variable_index(root_node,index_to_code):
    if root_node is None:
        return []
    if (len(root_node.children)==0 or root_node.type in ['string_literal','string','character_literal']) and root_node.type!='comment':
        index=(root_node.start_point,root_node.end_point)
        code = get_code_from_node(index[0],index[1],index_to_code)
        if code:
            return [(root_node.start_point,root_node.end_point)]
        else:
            return []
    else:
        code_tokens=[]
        for child in root_node.children:
            code_tokens+=tree_to_variable_index(child,index_to_code)
        return code_tokens
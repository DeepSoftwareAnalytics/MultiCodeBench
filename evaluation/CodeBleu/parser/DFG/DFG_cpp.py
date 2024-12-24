from tree_sitter import Language, Parser
from ..utils import (remove_comments_and_docstrings,
                   tree_to_token_index,
                   index_to_code_token,
                   tree_to_variable_index)

def find_child_by_type(root_node, target_type):
    for child in root_node.children:
        if child.type == target_type:
            return child
    return None
def get_code_from_node(start, end, index_to_code):
    codes = []
    
    for (s_point, e_point), (idx, code) in index_to_code.items():
        if (s_point >= start and s_point <= end) or (e_point >= start and e_point <= end) or (start >= s_point and end <= e_point):
            codes.append(code)
            
    return ' '.join(codes)  

def DFG_cpp(root_node, index_to_code, states):
    if root_node is None:
        return [], states

    assignment = ['assignment_expression', 'compound_assignment_expression', 'for_in_clause']
    if_statement = ['if_statement']
    for_statement = ['for_statement']
    while_statement = ['while_statement']
    def_statement = ['parameter_declaration']
    do_first_statement = ['for_in_clause']
    states = states.copy()
    if (root_node.start_point, root_node.end_point) not in index_to_code:
        DFG = []
        for child in root_node.children:
            temp, states = DFG_cpp(child, index_to_code, states)
            DFG += temp
        return DFG, states

    if (len(root_node.children) == 0 or root_node.type in ['string_literal', 'character_literal', 'number_literal']) and root_node.type != 'comment':
        idx, code = index_to_code[(root_node.start_point, root_node.end_point)]
        if root_node.type == code:
            return [], states
        elif code in states:
            return [(code, idx, 'comesFrom', [code], states[code].copy())], states
        else:
            if root_node.type == 'identifier':
                states[code] = [idx]
            return [(code, idx, 'comesFrom', [], [])], states
        
    
    elif root_node.type in def_statement:
        
        name = root_node.child_by_field_name('declarator')
        value = root_node.child_by_field_name('value')
        DFG = []
        if name is None:
            return [], states
        
        if value is None:
            if name.children is None:
                return [], states
            
            indexes = tree_to_variable_index(name, index_to_code)
            for index in indexes:
                idx, code = index_to_code[index]
                DFG.append((code, idx, 'comesFrom', [], []))
                states[code] = [idx]
            return sorted(DFG, key=lambda x: x[1]), states
        else:
            name_indexes = tree_to_variable_index(name, index_to_code)
            value_indexes = tree_to_variable_index(value, index_to_code)
            temp, states = DFG_cpp(value, index_to_code, states)
            DFG += temp
            for index1 in name_indexes:
                idx1, code1 = index_to_code[index1]
                for index2 in value_indexes:
                    idx2, code2 = index_to_code[index2]
                    DFG.append((code1, idx1, 'comesFrom', [code2], [idx2]))
                states[code1] = [idx1]
            return sorted(DFG, key=lambda x: x[1]), states

    elif root_node.type in assignment:
        left_nodes = [x for x in root_node.child_by_field_name('left').children if x.type != ',']
        right_nodes = [x for x in root_node.child_by_field_name('right').children if x.type != ',']

        if len(right_nodes) != len(left_nodes):
            left_nodes = [root_node.child_by_field_name('left')]
            right_nodes = [root_node.child_by_field_name('right')]
        DFG = []
        for node in right_nodes:
            temp, states = DFG_cpp(node, index_to_code, states)
            DFG += temp

        for left_node, right_node in zip(left_nodes, right_nodes):
            left_tokens_index = tree_to_variable_index(left_node, index_to_code)
            right_tokens_index = tree_to_variable_index(right_node, index_to_code)
            temp = []
            for token1_index in left_tokens_index:
                idx1, code1 = index_to_code[token1_index]
                temp.append((code1, idx1, 'computedFrom', [index_to_code[x][1] for x in right_tokens_index],
                             [index_to_code[x][0] for x in right_tokens_index]))
                states[code1] = [idx1]
            DFG += temp
        return sorted(DFG, key=lambda x: x[1]), states

    elif root_node.type in if_statement:
        DFG = []
        current_states = states.copy()
        others_states = []
        tag = False
        if 'else' in root_node.type:
            tag = True
        for child in root_node.children:
            if 'else' in child.type:
                tag = True
            if child.type not in ['elif_clause', 'else_clause']:
                temp, current_states = DFG_cpp(child, index_to_code, current_states)
                DFG += temp
            else:
                temp, new_states = DFG_cpp(child, index_to_code, states)
                DFG += temp
                others_states.append(new_states)
        others_states.append(current_states)
        if tag is False:
            others_states.append(states)
        new_states = {}
        for dic in others_states:
            for key in dic:
                if key not in new_states:
                    new_states[key] = dic[key].copy()
                else:
                    new_states[key] += dic[key]
        for key in new_states:
            new_states[key] = sorted(list(set(new_states[key])))
        return sorted(DFG, key=lambda x: x[1]), new_states

    elif root_node.type in for_statement:

        DFG = []
        declaration_node = None
        condition_node = None
        update_node = None
        block_node = None

        for child in root_node.children:
            if child.type == 'declaration':
                declaration_node = child
            elif child.type == 'binary_expression':  
                condition_node = child
            elif child.type == 'update_expression':
                update_node = child
            elif child.type == 'compound_statement':  
                block_node = child

        if declaration_node:
            temp, states = DFG_cpp(declaration_node, index_to_code, states)
            DFG += temp

        if condition_node:
            temp, states = DFG_cpp(condition_node, index_to_code, states)
            DFG += temp

        if update_node:
            temp, states = DFG_cpp(update_node, index_to_code, states)
            DFG += temp

        if block_node:
            temp, states = DFG_cpp(block_node, index_to_code, states)
            DFG += temp

        dic = {}
        for x in DFG:
            if (x[0], x[1], x[2]) not in dic:
                dic[(x[0], x[1], x[2])] = [x[3], x[4]]
            else:
                dic[(x[0], x[1], x[2])][0] = list(set(dic[(x[0], x[1], x[2])][0] + x[3]))
                dic[(x[0], x[1], x[2])][1] = sorted(list(set(dic[(x[0], x[1], x[2])][1] + x[4])))
        DFG = [(x[0], x[1], x[2], y[0], y[1]) for x, y in sorted(dic.items(), key=lambda t: t[0][1])]
        return sorted(DFG, key=lambda x: x[1]), states

    elif root_node.type in while_statement:
        DFG = []
        for i in range(2):
            for child in root_node.children:
                temp, states = DFG_cpp(child, index_to_code, states)
                DFG += temp
        dic = {}
        for x in DFG:
            if (x[0], x[1], x[2]) not in dic:
                dic[(x[0], x[1], x[2])] = [x[3], x[4]]
            else:
                dic[(x[0], x[1], x[2])][0] = list(set(dic[(x[0], x[1], x[2])][0] + x[3]))
                dic[(x[0], x[1], x[2])][1] = sorted(list(set(dic[(x[0], x[1], x[2])][1] + x[4])))
        DFG = [(x[0], x[1], x[2], y[0], y[1]) for x, y in sorted(dic.items(), key=lambda t: t[0][1])]
        return sorted(DFG, key=lambda x: x[1]), states

    else:
        DFG = []
        for child in root_node.children:
            if child.type == "ERROR":
                continue
            if child.type in do_first_statement:
                temp, states = DFG_cpp(child, index_to_code, states)
                DFG += temp
        for child in root_node.children:
            if child.type == "ERROR":
                continue
            if child.type not in do_first_statement:
                temp, states = DFG_cpp(child, index_to_code, states)
                DFG += temp
        return sorted(DFG, key=lambda x: x[1]), states
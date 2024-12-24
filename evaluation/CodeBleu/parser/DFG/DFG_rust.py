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


def DFG_rust(root_node, index_to_code, states):

    if root_node is None:
        return [], states
    assignment = ['assignment', 'augmented_assignment', 'let_declaration']
    if_statement = ['if_expression']
    for_statement = ['for_expression']
    while_statement = ['while_expression']
    loop_statement = ['loop_expression']
    match_statement = ['match_expression']
    function_param = ['param']
    states = states.copy()

    if (len(root_node.children) == 0 or root_node.type in ['string_literal', 'char_literal', 'literal']) and root_node.type != 'comment':
        code = get_code_from_node(root_node.start_point,root_node.end_point,index_to_code)
        idx = root_node.start_point,root_node.end_point
        if root_node.type == code:
            return [], states
        elif code in states:
            return [(code, idx, 'comesFrom', [code], states[code].copy())], states
        else:
            if root_node.type == 'identifier':
                states[code] = [idx]
            return [(code, idx, 'comesFrom', [], [])], states

    elif root_node.type in function_param:
        name = root_node.child_by_field_name('name')
        value = root_node.child_by_field_name('value')
        DFG = []
        if value is None:
            indices = tree_to_variable_index(name, index_to_code)
            for index in indices:
                code = get_code_from_node(index[0],index[1],index_to_code)
                idx = index
                DFG.append((code, idx, 'comesFrom', [], []))
                states[code] = [idx]
            return sorted(DFG, key=lambda x: x[1]), states
        else:
            name_indices = tree_to_variable_index(name, index_to_code)
            value_indices = tree_to_variable_index(value, index_to_code)
            temp, states = DFG_rust(value, index_to_code, states)
            DFG += temp
            for index1 in name_indices:
                code1 = get_code_from_node(index1[0],index1[1],index_to_code)
                idx1 = index1
                for index2 in value_indices:
                    code2 = get_code_from_node(index2[0],index2[1],index_to_code)
                    idx2 = index2
                    DFG.append((code1, idx1, 'comesFrom', [code2], [idx2]))
                states[code1] = [idx1]
            return sorted(DFG, key=lambda x: x[1]), states

    elif root_node.type in assignment:
        if root_node.type == 'for_expression':
            right_nodes = [root_node.children[-1]]
            left_nodes = [root_node.child_by_field_name('left')]
        else:
            if root_node.child_by_field_name('right') is None:
                return [], states
            left_nodes = [x for x in root_node.child_by_field_name('left').children if x.type != ',']
            right_nodes = [x for x in root_node.child_by_field_name('right').children if x.type != ',']
            if len(right_nodes) != len(left_nodes):
                left_nodes = [root_node.child_by_field_name('left')]
                right_nodes = [root_node.child_by_field_name('right')]
            if len(left_nodes) == 0:
                left_nodes = [root_node.child_by_field_name('left')]
            if len(right_nodes) == 0:
                right_nodes = [root_node.child_by_field_name('right')]
        DFG = []
        for node in right_nodes:
            temp, states = DFG_rust(node, index_to_code, states)
            DFG += temp

        for left_node, right_node in zip(left_nodes, right_nodes):
            left_tokens_index = tree_to_variable_index(left_node, index_to_code)
            right_tokens_index = tree_to_variable_index(right_node, index_to_code)
            temp = []
            for token1_index in left_tokens_index:
                code1 = get_code_from_node(token1_index[0],token1_index[1],index_to_code)
                idx1 = token1_index
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
            if child.type not in ['else_clause']:
                temp, current_states = DFG_rust(child, index_to_code, current_states)
                DFG += temp
            else:
                temp, new_states = DFG_rust(child, index_to_code, states)
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
        iterator_node = None
        block_node = None
        for child in root_node.children:
            if child.type == 'identifier' or child.type == 'binary_expression' or child.type == 'call_expression':
                iterator_node = child
            elif child.type == 'block':
                block_node = child

        if iterator_node:
            temp, states = DFG_rust(iterator_node, index_to_code, states)
            DFG += temp

        if block_node:
            temp, states = DFG_rust(block_node, index_to_code, states)
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
                temp, states = DFG_rust(child, index_to_code, states)
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

    elif root_node.type in loop_statement:
        DFG = []

        for child in root_node.children:
            if child.type == 'loop':  
                temp, states = DFG_rust(child, index_to_code, states)
                DFG += temp

            elif child.type == 'block':  
                temp, states = DFG_rust(child, index_to_code, states)
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

    elif root_node.type in match_statement:
        DFG = []
        for child in root_node.children:
            temp, states = DFG_rust(child, index_to_code, states)
            DFG += temp
        return sorted(DFG, key=lambda x: x[1]), states

    else:
        DFG = []
        for child in root_node.children:
            temp, states = DFG_rust(child, index_to_code, states)
            DFG += temp
        return sorted(DFG, key=lambda x: x[1]), states
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


def DFG_solidity(root_node, index_to_code, states):
    if root_node is None:
        return [], states

    if (root_node.start_point, root_node.end_point) not in index_to_code:
        DFG = []
        for child in root_node.children:
            temp, states = DFG_solidity(child, index_to_code, states)
            DFG += temp
        return DFG, states
    
    
    assignment = ['variable_declaration', 'variable_assignment']
    if_statement = ['if_statement']
    for_statement = ['for_statement']
    while_statement = ['while_statement']
    require_statement = ['require_statement']
    return_statement = ['return_statement']
    function_definition = ['function_definition']
    expression_statement = ['expression_statement']

    states = states.copy()

    if (len(root_node.children) == 0 or root_node.type in ['string_literal', 'number_literal', 'boolean_literal']) and root_node.type != 'comment':
        idx, code = index_to_code[(root_node.start_point, root_node.end_point)]
        if root_node.type == code:
            return [], states
        elif code in states:
            return [(code, idx, 'comesFrom', [code], states[code].copy())], states
        else:
            if root_node.type == 'identifier':
                states[code] = [idx]
            return [(code, idx, 'comesFrom', [], [])], states

    elif root_node.type in assignment:
        left_node = root_node.child_by_field_name('left')
        right_node = root_node.child_by_field_name('right')

        DFG = []
        temp, states = DFG_solidity(right_node, index_to_code, states)
        DFG += temp

        left_tokens_index = tree_to_variable_index(left_node, index_to_code)
        right_tokens_index = tree_to_variable_index(right_node, index_to_code)

        for token1_index in left_tokens_index:
            idx1, code1 = index_to_code[token1_index]
            DFG.append((code1, idx1, 'computedFrom', [index_to_code[x][1] for x in right_tokens_index],
                        [index_to_code[x][0] for x in right_tokens_index]))
            states[code1] = [idx1]

        return sorted(DFG, key=lambda x: x[1]), states

    elif root_node.type in if_statement:
        DFG = []
        current_states = states.copy()
        others_states = []

        for child in root_node.children:
            temp, new_states = DFG_solidity(child, index_to_code, states)
            DFG += temp
            others_states.append(new_states)

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
        for _ in range(2): 
            temp, states = DFG_solidity(root_node, index_to_code, states)
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
        for _ in range(2):  
            temp, states = DFG_solidity(root_node, index_to_code, states)
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

    elif root_node.type in function_definition:
        DFG = []
        for child in root_node.children:
            temp, states = DFG_solidity(child, index_to_code, states)
            DFG += temp
        return sorted(DFG, key=lambda x: x[1]), states

    else:
        DFG = []
        for child in root_node.children:
            temp, states = DFG_solidity(child, index_to_code, states)
            DFG += temp

        return sorted(DFG, key=lambda x: x[1]), states
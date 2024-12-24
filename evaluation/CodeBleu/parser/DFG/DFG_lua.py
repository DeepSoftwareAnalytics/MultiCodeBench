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


def DFG_lua(root_node, index_to_code, states):
    assignment = ['assignment', 'local_assignment']
    if_statement = ['if_statement']
    for_statement = ['for_statement', 'for_numeric_statement', 'for_generic_statement']
    while_statement = ['while_statement']
    repeat_statement = ['repeat_statement']
    def_statement = ['function_definition', 'local_function_definition']
    states = states.copy()
    if (root_node.start_point, root_node.end_point) not in index_to_code:
        DFG = []
        for child in root_node.children:
            temp, states = DFG_lua(child, index_to_code, states)
            DFG += temp
        return DFG, states
    if (len(root_node.children) == 0 or root_node.type in ['string_literal', 'number_literal', 'boolean_literal', 'nil_literal']) and root_node.type != 'comment':
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
        name = root_node.child_by_field_name('name')
        parameters = root_node.child_by_field_name('parameters')
        body = root_node.child_by_field_name('body')
        DFG = []
        if parameters:
            for param in parameters.children:
                if param.type == 'identifier':
                    idx, code = index_to_code[(param.start_point, param.end_point)]
                    DFG.append((code, idx, 'comesFrom', [], []))
                    states[code] = [idx]
        if body:
            temp, states = DFG_lua(body, index_to_code, states)
            DFG += temp
        return sorted(DFG, key=lambda x: x[1]), states

    elif root_node.type in assignment:
        left_nodes = [x for x in root_node.child_by_field_name('left').children if x.type != ',']
        right_nodes = [x for x in root_node.child_by_field_name('right').children if x.type != ',']
        DFG = []
        for node in right_nodes:
            temp, states = DFG_lua(node, index_to_code, states)
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
        for child in root_node.children:
            if child.type not in ['elseif_clause', 'else_clause']:
                temp, current_states = DFG_lua(child, index_to_code, current_states)
                DFG += temp
            else:
                temp, new_states = DFG_lua(child, index_to_code, states)
                DFG += temp
                others_states.append(new_states)
        others_states.append(current_states)
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
        for i in range(2):
            left_nodes = [x for x in root_node.child_by_field_name('left').children if x.type != ',']
            right_nodes = [root_node.child_by_field_name('right')]
            if len(left_nodes) == 0:
                left_nodes = [root_node.child_by_field_name('left')]
            for node in right_nodes:
                temp, states = DFG_lua(node, index_to_code, states)
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
            if root_node.child_by_field_name('body'):
                temp, states = DFG_lua(root_node.child_by_field_name('body'), index_to_code, states)
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
                temp, states = DFG_lua(child, index_to_code, states)
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

    elif root_node.type in repeat_statement:
        DFG = []
        for i in range(2):
            for child in root_node.children:
                temp, states = DFG_lua(child, index_to_code, states)
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

    elif root_node.type == 'local_declaration':
        DFG = []
        left_nodes = [x for x in root_node.child_by_field_name('names').children if x.type != ',']
        right_nodes = [x for x in root_node.child_by_field_name('values').children if x.type != ',']

        for right_node in right_nodes:
            temp, states = DFG_lua(right_node, index_to_code, states)
            DFG += temp

        for left_node, right_node in zip(left_nodes, right_nodes):
            left_tokens_index = tree_to_variable_index(left_node, index_to_code)
            right_tokens_index = tree_to_variable_index(right_node, index_to_code)
            temp = []
            for token1_index in left_tokens_index:
                idx1, code1 = index_to_code[token1_index]
                temp.append((code1, idx1, 'computedFrom', 
                            [index_to_code[x][1] for x in right_tokens_index],
                            [index_to_code[x][0] for x in right_tokens_index]))
                states[code1] = [idx1]
            DFG += temp

        return sorted(DFG, key=lambda x: x[1]), states
    else:
        DFG = []
        for child in root_node.children:
            temp, states = DFG_lua(child, index_to_code, states)
            DFG += temp
        return sorted(DFG, key=lambda x: x[1]), states
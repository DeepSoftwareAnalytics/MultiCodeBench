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


def DFG_scala(root_node, index_to_code, states):    
    assignment_types = ['assignment', 'val_definition', 'var_definition', 'var_declaration']    
    if_statement = ['if_statement']
    for_statement = ['for_statement']
    while_statement = ['while_statement']
    def_statement = ['function_definition']
    states = states.copy()

    if (len(root_node.children) == 0 or root_node.type in ['string_literal', 'character_literal']) and root_node.type != 'comment':
        code = get_code_from_node(root_node.start_point, root_node.end_point,index_to_code)
        idx = (root_node.start_point, root_node.end_point)
        if root_node.type == code:
            return [], states
        elif code in states:
            return [(code, idx, 'comesFrom', [code], states[code].copy())], states
        else:
            if root_node.type == 'identifier':
                states[code] = [idx]
            return [(code, idx, 'comesFrom', [], [])], states

    elif root_node.type in def_statement:
        DFG = []
        params = root_node.child_by_field_name('parameters')
        body = root_node.child_by_field_name('body')
        if params is not None:
            for param in params.children:
                indexs = tree_to_variable_index(param, index_to_code)
                for index in indexs:
                    code = get_code_from_node(index[0],index[1],index_to_code)
                    idx = index
                    DFG.append((code, idx, 'comesFrom', [], []))
                    states[code] = [idx]
        if body is not None:
            temp, states = DFG_scala(body, index_to_code, states)
            DFG += temp
        return sorted(DFG, key=lambda x: x[1]), states

    elif root_node.type in assignment_types:
        DFG = []

        if root_node.type == 'val_definition':
            pattern_node = root_node.child_by_field_name('pattern')  
            value_node = root_node.child_by_field_name('value')  
            type_node = root_node.child_by_field_name('type') 

            if pattern_node is None or value_node is None:
                return [], states

            DFG = []

            if type_node:
                type_tokens_index = tree_to_variable_index(type_node, index_to_code)
                for token1_index in type_tokens_index:
                    code1 = get_code_from_node(token1_index[0], token1_index[1], index_to_code)
                    idx1 = token1_index
                    DFG.append((code1, idx1, 'typedAs', [], []))

            variable_tokens_index = tree_to_variable_index(pattern_node, index_to_code)
            value_tokens_index = tree_to_variable_index(value_node, index_to_code)

            for token1_index in variable_tokens_index:
                code1 = get_code_from_node(token1_index[0], token1_index[1], index_to_code)
                idx1 = token1_index
                temp = []
                for token2_index in value_tokens_index:
                    code2 = get_code_from_node(token2_index[0], token2_index[1], index_to_code)
                    idx2 = token2_index
                    temp.append((code1, idx1, 'computedFrom', [code2], [idx2]))
                DFG += temp
                states[code1] = [idx1]

            return sorted(DFG, key=lambda x: x[1]), states

        elif root_node.type == 'var_definition':
            pattern_node = root_node.child_by_field_name('pattern')  
            value_node = root_node.child_by_field_name('value')  
            type_node = root_node.child_by_field_name('type')  

            if pattern_node is None or value_node is None:
                print(f"Warning: 'pattern' or 'value' not found in {root_node.type}")
                return [], states

            DFG = []

            if type_node:
                type_tokens_index = tree_to_variable_index(type_node, index_to_code)
                for token1_index in type_tokens_index:
                    code1 = get_code_from_node(token1_index[0], token1_index[1], index_to_code)
                    idx1 = token1_index
                    DFG.append((code1, idx1, 'typedAs', [], []))

            variable_tokens_index = tree_to_variable_index(pattern_node, index_to_code)
            value_tokens_index = tree_to_variable_index(value_node, index_to_code)

            for token1_index in variable_tokens_index:
                code1 = get_code_from_node(token1_index[0], token1_index[1], index_to_code)
                idx1 = token1_index
                temp = []
                for token2_index in value_tokens_index:
                    code2 = get_code_from_node(token2_index[0], token2_index[1], index_to_code)
                    idx2 = token2_index
                    temp.append((code1, idx1, 'computedFrom', [code2], [idx2]))
                DFG += temp
                states[code1] = [idx1]

            return sorted(DFG, key=lambda x: x[1]), states

        elif root_node.type == 'var_declaration':
            name_nodes = root_node.child_by_field_name('name')  
            type_node = root_node.child_by_field_name('type') 

            if name_nodes is None or type_node is None:
                return [], states
            DFG = []
            type_tokens_index = tree_to_variable_index(type_node, index_to_code)
            type_code_list = []
            for token2_index in type_tokens_index:
                code2 = get_code_from_node(token2_index[0], token2_index[1], index_to_code)
                idx2 = token2_index
                type_code_list.append((code2, idx2))

            for name_node in name_nodes.named_children:
                variable_tokens_index = tree_to_variable_index(name_node, index_to_code)

                for token1_index in variable_tokens_index:
                    code1 = get_code_from_node(token1_index[0], token1_index[1], index_to_code)
                    idx1 = token1_index
                    temp = []
                    for code2, idx2 in type_code_list:
                        temp.append((code1, idx1, 'typedAs', [code2], [idx2]))
                    DFG += temp
                    states[code1] = [idx1]

            return sorted(DFG, key=lambda x: x[1]), states

        elif root_node.type == 'assignment_expression':
            left_node = root_node.child_by_field_name('left')
            right_node = root_node.child_by_field_name('right')

            if left_node is None or right_node is None:
                return [], states

            DFG = []
            left_tokens_index = tree_to_variable_index(left_node, index_to_code)
            if not left_tokens_index:
                print(f"Warning: No tokens found in 'left' expression of {root_node.type}")

            right_tokens_index = tree_to_variable_index(right_node, index_to_code)
            if not right_tokens_index:
                print(f"Warning: No tokens found in 'right' expression of {root_node.type}")

            for left_token_index in left_tokens_index:
                code1 = get_code_from_node(left_token_index[0], left_token_index[1], index_to_code)
                idx1 = left_token_index
                temp = []
                for right_token_index in right_tokens_index:
                    code2 = get_code_from_node(right_token_index[0], right_token_index[1], index_to_code)
                    idx2 = right_token_index
                    temp.append((code1, idx1, 'computedFrom', [code2], [idx2]))
                DFG += temp
                states[code1] = [idx1]
            return sorted(DFG, key=lambda x: x[1]), states
        else:
            DFG = []
            for child in root_node.children:
                temp, states = DFG_scala(child, index_to_code, states)
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
                temp, current_states = DFG_scala(child, index_to_code, current_states)
                DFG += temp
            else:
                temp, new_states = DFG_scala(child, index_to_code, states)
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
        for i in range(2):
            right_nodes = [x for x in root_node.child_by_field_name('right').children if x.type != ',']
            left_nodes = [x for x in root_node.child_by_field_name('left').children if x.type != ',']
            if len(right_nodes) != len(left_nodes):
                left_nodes = [root_node.child_by_field_name('left')]
                right_nodes = [root_node.child_by_field_name('right')]
            if len(left_nodes) == 0:
                left_nodes = [root_node.child_by_field_name('left')]
            if len(right_nodes) == 0:
                right_nodes = [root_node.child_by_field_name('right')]
            for node in right_nodes:
                temp, states = DFG_scala(node, index_to_code, states)
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
            if root_node.children[-1].type == "block":
                temp, states = DFG_scala(root_node.children[-1], index_to_code, states)
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
                temp, states = DFG_scala(child, index_to_code, states)
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
            temp, states = DFG_scala(child, index_to_code, states)
            DFG += temp

        return sorted(DFG, key=lambda x: x[1]), states

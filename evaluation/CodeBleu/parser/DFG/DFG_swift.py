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

def DFG_swift(root_node, index_to_code, states):

    assignment = ['variable_declaration']
    
    if_statement = ['if_statement']
    for_statement = ['for_statement']
    while_statement = ['while_statement']
    switch_statement = ['switch_statement']

    func_def = ['function_declaration']
    class_def = ['class_declaration']
    guard_statement = ['guard_statement']
    return_statement = ['return_statement']
    protocol = ['protocol_declaration']
    extension = ['extension_declaration']
    initializer_declaration = ['initializer_declaration']
    defer_statement = ['defer_statement']
    error_handling = [ 'catch_clause', 'throw_statement']

    states = states.copy()
    if root_node is None:
        return [], states

    if (len(root_node.children) == 0 or root_node.type in ['string_literal', 'character_literal', 'number_literal']) and root_node.type != 'comment':
        
        idx_range = (root_node.start_point, root_node.end_point)
        
        if idx_range in index_to_code:
            idx, code = index_to_code[idx_range]
            idx = (root_node.start_point, root_node.end_point)
        else:
            return [], states  
        
        if root_node.type == code:
            return [], states
        elif code in states:
            return [(code, idx, 'comesFrom', [code], states[code].copy())], states
        else:
            if root_node.type == 'identifier':
                states[code] = [idx]
            return [(code, idx, 'comesFrom', [], [])], states
    
    elif root_node.type == 'call_expression':
        DFG = []

        function_node = find_child_by_type(root_node, ['simple_identifier', 'navigation_expression'])
        if function_node:
            function_indexs = tree_to_variable_index(function_node, index_to_code)
            for index in function_indexs:
                idx, code = index_to_code[index]
                idx = index
                DFG.append((code, idx, 'call', [], []))
                states[code] = [idx]

        call_suffix_node = find_child_by_type(root_node, 'call_suffix')
        if call_suffix_node:
            for child in call_suffix_node.children:
                temp_DFG, states = DFG_swift(child, index_to_code, states)
                DFG += temp_DFG

        for child in root_node.children:
            if child.type not in ['simple_identifier', 'call_suffix']:
                temp_DFG, states = DFG_swift(child, index_to_code, states)
                DFG += temp_DFG

        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states


    elif root_node.type == 'variable_declaration':
        DFG = []
        identifier_node = find_child_by_type(root_node, 'identifier')
        if identifier_node:
            identifier_indexs = tree_to_variable_index(identifier_node, index_to_code)
            for index in identifier_indexs:
                idx, code = index_to_code[index]
                idx = index
                DFG.append((code, idx, 'declaration', [], []))  
                states[code] = [idx]

        type_node = find_child_by_type(root_node, 'type')
        if type_node:
            type_indexs = tree_to_variable_index(type_node, index_to_code)
            for type_index in type_indexs:
                try:
                    type_code = index_to_code[type_index][1]
                    DFG.append((type_code, type_index, 'type', [], []))  
                except:
                    pass

        value_node = find_child_by_type(root_node, 'value')
        if value_node:
            temp_DFG, states = DFG_swift(value_node, index_to_code, states)
            DFG += temp_DFG

            identifier_indexs = tree_to_variable_index(identifier_node, index_to_code)
            value_indexs = tree_to_variable_index(value_node, index_to_code)
            for var_index in identifier_indexs:
                idx1, code1 = index_to_code[var_index]
                idx1 = var_index
                DFG.append((code1, idx1, 'comesFrom', [index_to_code[x][1] for x in value_indexs],
                            [index_to_code[x][0] for x in value_indexs]))
                states[code1] = [idx1]
        if hasattr(root_node, 'children') and root_node.children:
            for child in root_node.children:
                temp_DFG, states = DFG_swift(child, index_to_code, states)
                DFG += temp_DFG
        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states

    elif root_node.type == 'if_expression':
        DFG = []
        current_states = states.copy()
        others_states = []
        
        has_else = any(child.type == 'else_clause' for child in root_node.children)

        for child in root_node.children:
            if child.type in ['condition', 'additive_expression', 'comparison_expression', 'boolean_literal']:
                temp_DFG, current_states = DFG_swift(child, index_to_code, current_states)
                DFG += temp_DFG

            elif child.type == 'control_structure_body':
                temp_DFG, current_states = DFG_swift(child, index_to_code, current_states)
                DFG += temp_DFG

            elif child.type == 'else_clause':
                temp_DFG, new_states = DFG_swift(child, index_to_code, states)
                DFG += temp_DFG
                others_states.append(new_states)

        others_states.append(current_states)

        if not has_else:
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

        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), new_states

    elif root_node.type == 'function_declaration':
        DFG = []

        func_name_node = find_child_by_type(root_node, ['identifier', 'operator'])
        if func_name_node:
            func_name_indexs = tree_to_variable_index(func_name_node, index_to_code)
            for index in func_name_indexs:
                idx, code = index_to_code[index]
                idx = index
                DFG.append((code, idx, 'function', [], []))  
                states[code] = [idx]

        modifiers_node = find_child_by_type(root_node, 'modifier')
        if modifiers_node:
            for modifier in modifiers_node.children:
                modifier_code = get_code_from_node(modifier.start_point, modifier.end_point, index_to_code)
                DFG.append((modifier_code, (modifier.start_point, modifier.end_point), 'modifier', [], []))

        parameter_list_node = find_child_by_type(root_node, 'parameter_list')
        if parameter_list_node:
            for param in parameter_list_node.children:
                if param.type == 'parameter':  
                    name_node = find_child_by_type(param, 'identifier')
                    type_node = find_child_by_type(param, 'type')

                    if name_node:
                        name_indexs = tree_to_variable_index(name_node, index_to_code)
                        for index in name_indexs:
                            idx, code = index_to_code[index]
                            idx = index
                            DFG.append((code, idx, 'parameter', [], []))  
                            states[code] = [idx]

                    if type_node:
                        type_indexs = tree_to_variable_index(type_node, index_to_code)
                        for type_index in type_indexs:
                            type_code = index_to_code[type_index][1]
                            DFG.append((type_code, type_index, 'type', [], []))  

        return_type_node = find_child_by_type(root_node, 'type')
        if return_type_node:
            return_type_indexs = tree_to_variable_index(return_type_node, index_to_code)
            for return_type_index in return_type_indexs:
                return_type_index = (root_node.start_point, root_node.end_point)
                if return_type_index in index_to_code:
                    return_type_code = index_to_code[return_type_index][1]
                

                if return_type_index in index_to_code:
                    return_type_code = index_to_code[return_type_index][1]
                    return_type_index = (root_node.start_point, root_node.end_point)
                    DFG.append((return_type_code, return_type_index, 'return_type', [], []))

        for child in root_node.children:
            if child.type not in ['parameter_list', 'modifier']:
                temp, states = DFG_swift(child, index_to_code, states) 
                DFG += temp

        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states
    elif root_node.type == 'guard_expression':  
        DFG = []

        condition_node = find_child_by_type(root_node, 'condition')
        if condition_node:
            temp_DFG, states = DFG_swift(condition_node, index_to_code, states)
            DFG += temp_DFG

        else_node = find_child_by_type(root_node, 'else_clause')  
        if else_node:
            temp_DFG, states = DFG_swift(else_node, index_to_code, states)
            DFG += temp_DFG

        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states
    
    elif root_node.type == 'for_statement':
        DFG = []

        loop_var_node = find_child_by_type(root_node, 'identifier')
        if not loop_var_node:
            loop_var_node = find_child_by_type(root_node, 'value_binding_pattern')

        iterable_node = None
        for i, child in enumerate(root_node.children):
            if child.type == 'in' and i + 1 < len(root_node.children):
                iterable_node = root_node.children[i + 1] 

        body_node = None
        for child in root_node.children:
            if child.type in ['brace_stmt', 'block', 'control_structure_body']:  
                body_node = child
                break
        if loop_var_node:
            loop_var_indexs = tree_to_variable_index(loop_var_node, index_to_code)
            for index in loop_var_indexs:
                idx, code = index_to_code[index]
                idx = index
                DFG.append((code, idx, 'declaration', [], []))  
                states[code] = [idx]

        if iterable_node:
            iterable_indexs = tree_to_variable_index(iterable_node, index_to_code)
            for index in iterable_indexs:
                idx, code = index_to_code[index]
                idx = index
                DFG.append((code, idx, 'iteratesOver', [], []))  

        if body_node:
            temp, states = DFG_swift(body_node, index_to_code, states)
            DFG += temp

        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states
    

    elif root_node.type == 'while_statement':
        DFG = []

        condition_node = find_child_by_type(root_node, ['boolean', 'availability_condition', 'case_condition'])
        body_node = find_child_by_type(root_node, 'control_structure_body')

        if condition_node:
            temp, states = DFG_swift(condition_node, index_to_code, states)
            DFG += temp

        if body_node:
            for _ in range(2):  
                temp, states = DFG_swift(body_node, index_to_code, states)
                DFG += temp

        dic = {}
        for x in DFG:
            if (x[0], x[1], x[2]) not in dic:
                dic[(x[0], x[1], x[2])] = [x[3], x[4]]
            else:
                dic[(x[0], x[1], x[2])][0] = list(set(dic[(x[0], x[1], x[2])][0] + x[3]))
                dic[(x[0], x[1], x[2])][1] = sorted(list(set(dic[(x[0], x[1], x[2])][1] + x[4])))

        DFG = [(x[0], x[1], x[2], y[0], y[1]) for x, y in sorted(dic.items(), key=lambda t: t[0][1])]

        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states
    else:
        DFG = []
        for child in root_node.children:
            temp, states = DFG_swift(child, index_to_code, states)
            DFG += temp
        return sorted(DFG, key=lambda x: x[1]), states

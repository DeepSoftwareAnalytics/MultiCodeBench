from tree_sitter import Language, Parser
from ..utils import (remove_comments_and_docstrings,
                   tree_to_token_index,
                   index_to_code_token,
                   tree_to_variable_index)

def find_child_by_type(root_node, target_type):
    """
    Find child nodes of a specific type in the children of root_node
    """
    for child in root_node.children:
        if child.type == target_type:
            return child
    return None
def get_code_from_node(start, end, index_to_code):
    """
    Get the corresponding code according to the starting and ending points of the node, and handle multiple words
    """
    codes = []
    
    for (s_point, e_point), (idx, code) in index_to_code.items():

        if (s_point >= start and s_point <= end) or (e_point >= start and e_point <= end) or (start >= s_point and end <= e_point):
            codes.append(code)

    return ' '.join(codes)  

def DFG_c(root_node, index_to_code, states):

    assignment = ['assignment', 'augmented_assignment']
    if_statement = ['if_statement']
    for_statement = ['for_statement']
    while_statement = ['while_statement']
    declaration = ['declaration']
    states = states.copy() 

    if root_node is None:
        return [], states

    if (len(root_node.children) == 0 or root_node.type in ['string_literal', 'character_literal', 'numeric_literal']) and root_node.type != 'comment':        

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
        

    elif root_node.type in declaration:

        name = root_node.child_by_field_name('name')
        value = root_node.child_by_field_name('value')
        DFG = []
        if name is None:

            return [], states
        
        if value is None:
            if name.children is None:

                return [], states
            indexs = tree_to_variable_index(name, index_to_code)
            for index in indexs:
                code = get_code_from_node(index[0],index[1],index_to_code)
                idx = index
                DFG.append((code, idx, 'comesFrom', [], []))
                states[code] = [idx]
            return sorted(DFG, key=lambda x: x[1]), states
        else:
            name_indexs = tree_to_variable_index(name, index_to_code)
            value_indexs = tree_to_variable_index(value, index_to_code)
            temp, states = DFG_c(value, index_to_code, states)
            DFG += temp            
            for index1 in name_indexs:
                code1 = get_code_from_node(index1[0],index1[1],index_to_code)
                idx1 = index1

                for index2 in value_indexs:
                    code2 = get_code_from_node(index2[0],index2[1],index_to_code)
                    idx2 = index2
                    DFG.append((code1, idx1, 'comesFrom', [code2], [idx2]))
                states[code1] = [idx1]   
            return sorted(DFG, key=lambda x: x[1]), states

    elif root_node.type in assignment:
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
            temp, states = DFG_c(node, index_to_code, states)
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
                temp, current_states = DFG_c(child, index_to_code, current_states)
                DFG += temp
            else:
                temp, new_states = DFG_c(child, index_to_code, states)
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
            init_node = root_node.child_by_field_name('initializer')
            cond_node = root_node.child_by_field_name('condition')
            update_node = root_node.child_by_field_name('update')
            
            if init_node is not None:
                temp, states = DFG_c(init_node, index_to_code, states)
                DFG += temp
            if cond_node is not None:
                temp, states = DFG_c(cond_node, index_to_code, states)
                DFG += temp
            if update_node is not None:
                temp, states = DFG_c(update_node, index_to_code, states)
                DFG += temp
            
            if root_node.child_by_field_name('body').type == "compound_statement":
                temp, states = DFG_c(root_node.child_by_field_name('body'), index_to_code, states)
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
                temp, states = DFG_c(child, index_to_code, states)
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
            temp, states = DFG_c(child, index_to_code, states)
            DFG += temp
        
        return sorted(DFG, key=lambda x: x[1]), states
 
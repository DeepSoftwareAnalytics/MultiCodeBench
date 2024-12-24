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


def DFG_kotlin(root_node, index_to_code, states):
    # 定义各类节点类型
    # print(f"Processing node: {root_node}")
    assignment = ['assignment', 'variable_declaration', 'var_declaration']
    if_statement = ['if_expression']
    for_statement = ['for_statement']
    while_statement = ['while_statement']
    when_statement = ['when_expression']
    function_declaration = ['function_declaration']
    states = states.copy()
    if (root_node.start_point, root_node.end_point) not in index_to_code:
        # print(f"Warning: Index {root_node.start_point}-{root_node.end_point} not found in index_to_code, skipping to children.")
        DFG = []
        for child in root_node.children:
            temp, states = DFG_kotlin(child, index_to_code, states)
            DFG += temp
        return DFG, states
    if root_node is None:
        # print("root_node is None, skipping.")
        return [], states
    # def print_node(node, indent=""):
    #     print(f"{indent}- {node.type}")
    #     for child in node.children:
    #         print_node(child, indent + "  ")
    # print_node(root_node)
    # exit()
    # 处理终端节点
    # print("there")
    # if (len(root_node.children) == 0 or root_node.type in ['string_template', 'integer_literal', 'boolean_literal']) and root_node.type != 'comment':
    #     idx, code = index_to_code[(root_node.start_point, root_node.end_point)]
    if (len(root_node.children) == 0 or root_node.type in ['string_template', 'integer_literal', 'boolean_literal']) and root_node.type != 'comment':
        code = get_code_from_node(root_node.start_point, root_node.end_point, index_to_code)  
        idx = (root_node.start_point, root_node.end_point)
        if root_node.type == code:
            return [], states
        elif code in states:
            return [(code, idx, 'comesFrom', [code], states[code].copy())], states
        else:
            if root_node.type == 'simple_identifier':
                states[code] = [idx]
            return [(code, idx, 'comesFrom', [], [])], states
        
    elif root_node.type == 'identifier':
        DFG = []
        for child in root_node.children:
            temp, states = DFG_kotlin(child, index_to_code, states)
            DFG += temp
        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states
    
    # 处理函数参数的默认值
    elif root_node.type in function_declaration:
    # 初始化 DFG 列表
        DFG = []
        # 处理函数名（simple_identifier）
        func_name_node = find_child_by_type(root_node, 'simple_identifier')
        if func_name_node:
            func_name_indexs = tree_to_variable_index(func_name_node, index_to_code)
            for index in func_name_indexs:
                idx, code = index_to_code[index]
                idx = index
                DFG.append((code, idx, 'function', [], []))
                states[code] = [idx]

        # 处理修饰符（modifiers 节点）
        modifiers_node = find_child_by_type(root_node, 'modifiers')
        if modifiers_node:
            for modifier in modifiers_node.children:
                if modifier.type == 'member_modifier':
                    modifier_code = get_code_from_node(modifier.start_point, modifier.end_point, index_to_code)
                    DFG.append((modifier_code, (modifier.start_point, modifier.end_point), 'modifier', [], []))

        # 获取函数参数列表 (function_value_parameters) 节点
        parameter_list_node = find_child_by_type(root_node, 'function_value_parameters')
        if parameter_list_node:
            # 遍历函数参数
            # parameter_list = find_parameters_in_function_declaration(parameter_list_node)
            # if parameter_list:
            for param in parameter_list_node.children:
                name_node, type_node = None, None
                # 查找参数名称（simple_identifier）和类型（user_type）
                for child in param.children:
                    if child.type == 'simple_identifier':
                        name_node = child
                    elif child.type == 'user_type':
                        type_node = child

                # 获取参数名称
                if name_node:
                    name_indexs = tree_to_variable_index(name_node, index_to_code)
                    for index in name_indexs:
                        idx, code = index_to_code[index]
                        idx = index
                        DFG.append((code, idx, 'parameter', [], []))
                        states[code] = [idx]

                # 获取参数类型
                if type_node:
                    type_indexs = tree_to_variable_index(type_node, index_to_code)
                    for type_index in type_indexs:
                        type_code = index_to_code[type_index][1]
                        DFG.append((type_code, type_index, 'type', [], []))

        # 处理函数体（function_body 节点）
        func_body_node = find_child_by_type(root_node, 'function_body')
        if func_body_node:
            temp, states = DFG_kotlin(func_body_node, index_to_code, states)
            DFG += temp
        # 返回按位置排序的 DFG 和更新的状态
        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states

    # 处理赋值语句
    elif root_node.type == 'assignment':
        # 查找赋值操作符两侧的节点
        left_node = None
        right_node = None

        # 遍历子节点，识别赋值左侧和右侧
        for child in root_node.children:
            if child.type == 'simple_identifier':
                left_node = child  # 赋值左侧是变量
            elif child.type in [
                'additive_expression', 'binary_expression', 'call_expression', 'literal',
                'if_expression', 'when_expression', 'parenthesized_expression'
            ]:
                right_node = child  # 赋值右侧是表达式或值

        # 如果无法识别出赋值两侧，返回空的 DFG
        if right_node is None or left_node is None:
            return [], states

        # 处理右侧的表达式，递归生成其 DFG
        DFG = []
        temp, states = DFG_kotlin(right_node, index_to_code, states)  # 处理右侧表达式
        DFG += temp

        # 处理左侧变量，生成数据流依赖关系
        left_tokens_index = tree_to_variable_index(left_node, index_to_code)
        right_tokens_index = tree_to_variable_index(right_node, index_to_code)

        # 对每个左侧变量标记它依赖于右侧表达式或值
        for token1_index in left_tokens_index:
            idx1, code1 = index_to_code[token1_index]
            DFG.append((code1, idx1, 'computedFrom', [index_to_code[x][1] for x in right_tokens_index],
                        [index_to_code[x][0] for x in right_tokens_index]))
            states[code1] = [idx1]

        # 返回排序后的 DFG
        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states
    
    elif root_node.type == 'variable_declaration':
        DFG = []

        # 识别变量声明中的标识符（simple_identifier）和类型（user_type）
        identifier_node = find_child_by_type(root_node, 'simple_identifier')
        type_node = find_child_by_type(root_node, 'user_type')

        # 处理变量标识符
        if identifier_node:
            identifier_indexs = tree_to_variable_index(identifier_node, index_to_code)
            for index in identifier_indexs:
                idx, code = index_to_code[index]
                idx = index
                DFG.append((code, idx, 'declaration', [], []))  # 标记为变量声明
                states[code] = [idx]

        # 处理变量类型
        if type_node:
            type_indexs = tree_to_variable_index(type_node, index_to_code)
            for type_index in type_indexs:
                type_code = index_to_code[type_index][1]
                DFG.append((type_code, type_index, 'type', [], []))  # 标记变量类型

        # 返回排序后的 DFG
        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states
    # 处理if表达式
    elif root_node.type in if_statement:
        DFG = []
        current_states = states.copy()
        others_states = []
        has_else = any(child.type == 'else_clause' for child in root_node.children)

        for child in root_node.children:
            if child.type in ['comparison_expression', 'equality_expression', 'condition']:
                # 处理条件部分
                temp, current_states = DFG_kotlin(child, index_to_code, current_states)
                DFG += temp
            elif child.type == 'control_structure_body':
                # 处理主体部分（if body 或 else body）
                temp, current_states = DFG_kotlin(child, index_to_code, current_states)
                DFG += temp
            elif child.type == 'else_clause':
                # 处理 else 分支
                has_else = True
                temp, new_states = DFG_kotlin(child, index_to_code, states)
                DFG += temp
                others_states.append(new_states)  # 将 else 状态加入 others_states 列表

        # 如果没有 else 分支，添加当前状态作为默认状态
        if not has_else:
            others_states.append(states)

        # 合并 if 和 else 分支的状态
        others_states.append(current_states)
        new_states = {}

        # 合并不同分支的状态
        for dic in others_states:
            for key in dic:
                if key not in new_states:
                    new_states[key] = dic[key].copy()
                else:
                    new_states[key] += dic[key]
        # 去重并排序
        for key in new_states:
            new_states[key] = sorted(list(set(new_states[key])))

        # 返回 DFG 和合并后的状态
        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), new_states

    # 处理for语句
    elif root_node.type in for_statement:
        DFG = []
        # 识别循环变量和可迭代对象
        loop_variable_node = None
        loop_iterable_node = None
        body_node = None

        # 遍历 for_statement 的子节点，分别找出循环变量、可迭代对象和循环体
        for child in root_node.children:
            if child.type == 'simple_identifier':
                loop_variable_node = child
            elif child.type in ['call_expression', 'range_expression', 'collection_literal', 'navigation_expression']:
                loop_iterable_node = child
            elif child.type == 'control_structure_body':
                body_node = child

        # 处理可迭代对象，生成数据流图
        if loop_iterable_node:
            temp, states = DFG_kotlin(loop_iterable_node, index_to_code, states)
            DFG += temp

        # 处理循环变量，生成依赖关系
        if loop_variable_node:
            loop_var_index = tree_to_variable_index(loop_variable_node, index_to_code)
            iterable_index = tree_to_variable_index(loop_iterable_node, index_to_code)

            for token1_index in loop_var_index:
                idx1, code1 = index_to_code[token1_index]
                idx1 = token1_index
                DFG.append((code1, idx1, 'computedFrom', [index_to_code[x][1] for x in iterable_index],
                            [index_to_code[x][0] for x in iterable_index]))
                states[code1] = [idx1]

        # 处理循环体，递归生成数据流图
        if body_node:
            temp, states = DFG_kotlin(body_node, index_to_code, states)
            DFG += temp

        # 返回排序后的 DFG 和更新后的状态
        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states

    # 处理while语句
    elif root_node.type == 'while_statement':
        DFG = []
        # 查找 while 语句的条件和循环体
        condition_node = None
        body_node = None
        # 遍历 while_statement 的子节点，分别找出条件和循环体
        for child in root_node.children:
            if child.type in ['additive_expression', 'comparison_expression', 'boolean_literal', 'equality_expression']:
                condition_node = child
            elif child.type == 'control_structure_body':
                body_node = child
        # 处理条件部分，递归生成数据流图
        if condition_node:
            temp, states = DFG_kotlin(condition_node, index_to_code, states)
            DFG += temp

        # 处理循环体，递归生成数据流图
        if body_node:
            for _ in range(2):  # 循环至少执行两次
                temp, states = DFG_kotlin(body_node, index_to_code, states)
                DFG += temp

        # 去重并整理 DFG 数据
        dic = {}
        for x in DFG:
            if (x[0], x[1], x[2]) not in dic:
                dic[(x[0], x[1], x[2])] = [x[3], x[4]]
            else:
                dic[(x[0], x[1], x[2])][0] = list(set(dic[(x[0], x[1], x[2])][0] + x[3]))
                dic[(x[0], x[1], x[2])][1] = sorted(list(set(dic[(x[0], x[1], x[2])][1] + x[4])))

        DFG = [(x[0], x[1], x[2], y[0], y[1]) for x, y in sorted(dic.items(), key=lambda t: t[0][1])]

        # 返回排序后的 DFG 和更新后的状态
        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states

    # 处理when表达式
    elif root_node.type == 'when_expression':
        DFG = []
        current_states = states.copy()  # 复制当前状态
        others_states = []  # 存储分支状态

        # 遍历 when_expression 的子节点
        for child in root_node.children:
            if child.type == 'when_entry':  # 当遇到 when_entry 节点时
                temp, new_states = DFG_kotlin(child, index_to_code, current_states)
                DFG += temp
                others_states.append(new_states)

        # 合并所有的状态
        new_states = {}
        for dic in others_states:
            for key in dic:
                if key not in new_states:
                    new_states[key] = dic[key].copy()
                else:
                    new_states[key] += dic[key]

        # 去重并排序状态
        for key in new_states:
            new_states[key] = sorted(list(set(new_states[key])))

        # 返回生成的 DFG 和合并后的状态
        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), new_states

    elif root_node.type == 'when_entry':
        DFG = []

        # 处理 when 条件（when_condition）
        condition_node = find_child_by_type(root_node, 'when_condition')
        if condition_node:
            temp, states = DFG_kotlin(condition_node, index_to_code, states)
            DFG += temp

        # 处理 when 条件的执行块（control_structure_body 或 expression）
        body_node = find_child_by_type(root_node, 'control_structure_body') or find_child_by_type(root_node, 'expression')
        if body_node:
            temp, states = DFG_kotlin(body_node, index_to_code, states)
            DFG += temp

        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states

    elif root_node.type == 'when_condition':
        DFG = []

        # 递归处理 when 条件中的表达式
        for child in root_node.children:
            temp, states = DFG_kotlin(child, index_to_code, states)
            DFG += temp

        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states

    # 处理其他类型的节点
    elif root_node.type == 'call_suffix':
        DFG = []

        # 处理函数调用的参数部分：annotated_lambda, type_arguments, value_arguments
        annotated_lambda_node = find_child_by_type(root_node, 'annotated_lambda')
        type_arguments_node = find_child_by_type(root_node, 'type_arguments')
        value_arguments_node = find_child_by_type(root_node, 'value_arguments')

        # 处理 annotated_lambda（如存在）
        if annotated_lambda_node:
            temp, states = DFG_kotlin(annotated_lambda_node, index_to_code, states)
            DFG += temp

        # 处理 type_arguments（如存在）
        if type_arguments_node:
            temp, states = DFG_kotlin(type_arguments_node, index_to_code, states)
            DFG += temp

        # 处理 value_arguments（即函数调用的参数列表，如存在）
        if value_arguments_node:
            for argument in value_arguments_node.children:
                temp, states = DFG_kotlin(argument, index_to_code, states)
                DFG += temp

                # 获取每个参数的索引并生成数据流
                arg_tokens_index = tree_to_variable_index(argument, index_to_code)
                for token_index in arg_tokens_index:
                    idx, code = index_to_code[token_index]
                    idx = token_index
                    DFG.append((code, idx, 'argument', [], []))
                    states[code] = [idx]

        # 返回排序后的 DFG 和更新的状态
        return sorted(DFG, key=lambda x: (x[1][0], x[1][1])), states
    else:
        DFG = []
        for child in root_node.children:
            # print(10)
            # print("before",DFG)
            temp = []
            temp, states = DFG_kotlin(child, index_to_code, states)
            # print("final1",temp)
            DFG += temp
        # for entry in DFG:
        #     print(f"x[1]: {entry[1]}, type: {type(entry[1])}")
        # print('sort',sorted(DFG, key=lambda x: (x[1][0],x[1][1])), states)
        return sorted(DFG, key=lambda x: (x[1][0],x[1][1])), states
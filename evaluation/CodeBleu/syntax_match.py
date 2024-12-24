# Copyright (c) Microsoft Corporation. 
# Licensed under the MIT license.

from parser.DFG import DFG_python,DFG_java,DFG_go,DFG_php,DFG_javascript,DFG_csharp,DFG_typescript,DFG_solidity,DFG_cpp,DFG_c,DFG_rust,DFG_scala,DFG_lua,DFG_kotlin,DFG_swift
from parser import (remove_comments_and_docstrings,
                   tree_to_token_index,
                   index_to_code_token,
                   tree_to_variable_index,
                   remove_comments_and_docstrings1)
from tree_sitter import Language, Parser

dfg_function={
    'python':DFG_python,
    'java':DFG_java,
    'go':DFG_go,
    'php':DFG_php,
    'javascript':DFG_javascript,
    'c_sharp':DFG_csharp,
    'typescript':DFG_typescript,
    'solidity':DFG_solidity,
    'cpp':DFG_cpp,
    'c':DFG_c,
    'rust':DFG_rust,
    'scala':DFG_scala,
    'lua':DFG_lua,
    'kotlin':DFG_kotlin,
    'swift':DFG_swift
}

def calc_syntax_match(references, candidate, lang):
    return corpus_syntax_match([references], [candidate], lang)

def corpus_syntax_match(references, candidates):   
    match_count = 0  
    total_count = 0 
    for i in range(len(candidates)):
        reference = references[i]['ground_truth']
        candidate = candidates[i]['code']
        lang = references[i]['language'].lower()
        if lang == 'csharp':
            lang = 'c_sharp'
        LANGUAGE = Language('./build/my-languages.so', lang.lower())
        
        parser = Parser()
        parser.set_language(LANGUAGE)
        match_count = 0
        total_count = 0
        try:
            candidate=remove_comments_and_docstrings(candidate,lang)
        except Exception as e:
            print(f"Error removing comments from candidate: {e}")    
        try:
            reference=remove_comments_and_docstrings(reference,lang)
        except Exception as e:
            print(f"Error removing comments from candidate: {e}") 

        candidate_tree = parser.parse(bytes(candidate,'utf8')).root_node

        reference_tree = parser.parse(bytes(reference,'utf8')).root_node

        def get_all_sub_trees(root_node):
            node_stack = []
            sub_tree_sexp_list = []
            depth = 1
            node_stack.append([root_node, depth])
            while len(node_stack) != 0:
                cur_node, cur_depth = node_stack.pop()
                sub_tree_sexp_list.append([cur_node.sexp(), cur_depth])
                for child_node in cur_node.children:
                    if len(child_node.children) != 0:
                        depth = cur_depth + 1
                        node_stack.append([child_node, depth])
            return sub_tree_sexp_list
        cand_sexps = [x[0] for x in get_all_sub_trees(candidate_tree)]
        ref_sexps = get_all_sub_trees(reference_tree)
        
        for sub_tree, depth in ref_sexps:
            if sub_tree in cand_sexps:
                    match_count += 1
        total_count += len(ref_sexps)          
    
    if total_count == 0:
        return 0
    score = match_count / total_count if total_count > 0 else 0
    return score

# Copyright (c) Microsoft Corporation. 
# Licensed under the MIT license.

# -*- coding:utf-8 -*-
import argparse
import bleu
import weighted_ngram_match
import syntax_match
import dataflow_match
import os
from parser import (remove_comments_and_docstrings,remove_comments_and_docstrings1)
import re
import json,copy

def load_jsonl(fname):
    with open(fname, 'r', encoding='utf8') as f:
        lines = []
        for line in f:
            lines.append(json.loads(line))
        return lines
    
def dump_jsonl(obj, fname):
    with open(fname, 'w', encoding='utf8') as f:
        for item in obj:
            f.write(json.dumps(item) + '\n')

def make_weights(reference_tokens, lang):
    kw_file = "./keywords/{}.txt".format(lang)
    keywords = [x.strip() for x in open(kw_file, 'r', encoding='utf-8').readlines()]

    return {token: 1 if token in keywords else 0.2 \
            for token in reference_tokens}

def compute_codebleu(predict_results, references):
    
    lang = references[0]['language'].lower()

    alpha, beta, gamma, theta = 0.25,0.25,0.25,0.25
    
    if lang == 'csharp':
        lang = 'c_sharp'


    predict_results[0]['code'] = remove_comments_and_docstrings(predict_results[0]['code'],lang)
    ref = remove_comments_and_docstrings(references[0]['ground_truth'],lang)
    if ref is not None and not len(ref) == 0:
        references[0]['ground_truth'] = ref
    function_declaration_len = len(references[0]['function_declaration'])

    tokenized_pred = [x['code'][function_declaration_len:].split() for x in predict_results]
    tokenized_refs = [x['ground_truth'][function_declaration_len:].split() for x in references]
    
    ngram_match_score = bleu.corpus_bleu(references,predict_results)
    
    tokenized_refs_with_weights = []
    i = 0
    for reference_tokens in tokenized_refs:
        lang = references[i]['language'].lower()
        i += 1
        token_with_weight = [
            reference_tokens, make_weights(reference_tokens, lang)
        ]
        tokenized_refs_with_weights.append(token_with_weight)

    weighted_ngram_match_score = weighted_ngram_match.corpus_bleu(tokenized_refs_with_weights, tokenized_pred)
    
    syntax_match_score = syntax_match.corpus_syntax_match(references, predict_results)

    dataflow_match_score = dataflow_match.corpus_dataflow_match(references, predict_results)

    code_bleu_score = alpha * ngram_match_score \
                      + beta * weighted_ngram_match_score \
                      + gamma * syntax_match_score \
                      + theta * dataflow_match_score

    return code_bleu_score, (ngram_match_score, weighted_ngram_match_score, syntax_match_score, dataflow_match_score)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, required=True)
    parser.add_argument('--predict_result_base_path',type=str, required=True)
    args = parser.parse_args()
    domains = ['Block_chain','Cloud_service','Data_analysis','Deep_learning','Desktop_application',\
            'Distributed_system','Enterprise_application','Game','IoT','Mobile','Robot','Web']
    for domain in domains:
        totoal_score = 0
        # load ground truth
        reference_base_path = '/data/v1'
        reference_file_path = reference_base_path + '/' + domain + '.json'
        with open(reference_file_path,'r') as f:
            references = json.load(f)

        # load predict result
        predict_result_path = args.predict_result_base_path+'/'+args.model
        predict_result_file_path = predict_result_path + '/' + domain +'.jsonl'
        predict_results = load_jsonl(predict_result_file_path)

        predict_results1 = {item['instance_id']:item for item in predict_results}
        predict_results = predict_results1
        
        total_score = 0
        for i in range(len(references)):
            instance_id = references[i]['instance_id']
            reference = references[i]
            print(instance_id,reference['language'])

            for predict in predict_results[instance_id]['generation_result']:

                if reference['language'].lower() == 'php':
                    if not predict['code'].startswith('<?') or not predict['code'].startswith('\n<?'):
                        predict['code'] = '<?\n'+predict['code']
                    if not reference['ground_truth'].startswith('<?'):
                        reference['ground_truth'] = '<?\n' + reference['ground_truth']
                
                predict_copy = copy.copy(predict)
                # Compute CodeBLEU score for the individual pair
                code_bleu_score, (ngram_match_score, weighted_ngram_match_score, syntax_match_score, dataflow_match_score) = \
                    compute_codebleu([predict_copy], [reference])
                
                total_score += code_bleu_score * 100
                predict['CodeBleu_score'] = code_bleu_score * 100
        generation_results_with_score = []
        for value in predict_results.values():
            generation_results_with_score.append(value)
        dump_jsonl(generation_results_with_score,predict_result_file_path)
        

        


if __name__ == '__main__':
    main()
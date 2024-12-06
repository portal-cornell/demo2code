
import nltk
import nltk.translate.bleu_score as bleu

import re

import numpy as np

def filter_code(code):
    """
    Return:
        the code string fitered without say function
    """
    if "say" in code:
        after_say = code
        while "say" in after_say:
            _, _, after_say = after_say.partition("say")
            _, _, after_say = after_say.partition(")\n")

        return after_say
    else:
        return code
    

def compute_bleu_score_for_code(ground_truth_code, code):
    """
    BLEU score between the ground truth code and the LLM current code

    Return:
        the percent of match between the two code (max: 1)
    """
    ground_truth_code_filtered = filter_code(ground_truth_code)
    code_filtered = filter_code(code)

    ref = re.split(' |"|\n', ground_truth_code_filtered)
    ref = [x for x in ref if x != '']
    hyp = re.split(' |"|\n', code_filtered)
    hyp = [x for x in hyp if x != '']

    return bleu.sentence_bleu([ref], hyp)

def extract_exec_result(exec_status_dict, query_config_list):
    result_dict = {}

    for query_config in query_config_list:
        example_name, description_opt, id_num = query_config.split(',')

        result = exec_status_dict[example_name][description_opt][id_num]

        if description_opt == "none-specific":
            description_opt = "none"
        key = f"{example_name},{description_opt}"
        
        if key not in result_dict:
            result_dict[key] = []

        result_dict[key].append(result)

    return result_dict

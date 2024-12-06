"""
After running code generation and executing the code in the simulator, we need to evaluate the runs. This file
produces CSV files in the data directory under the results/overall with the execution, unit test, and token
matching results.
"""
import numpy as np
import yaml
import json

from scripts.overall_helpers.utils import *
from scripts.overall_helpers.eval_helper import compute_bleu_score_for_code, extract_exec_result

from scripts.robotouille_helpers.robotouille_template import robotouille_prompt_template

import re
import nltk.translate.bleu_score as bleu

from copy import deepcopy

def bleu_eval(lmp_name, prompt_version, demo_config_filename):
    """
    Given a query config, run token-wise comparison between the oracle code (spec2code) and the current model's code
    
    Return:
        a dictionary where the key is "{example_name},{description_opt}" and the value is the token comparison score for 
        each example that fits in the category
    """
    with open(f"./data/robotouille/demonstration_config/{demo_config_filename}.txt", "r") as fin:
        demo_config_list = fin.read().splitlines()

    result_dict = {}

    for i in range(len(demo_config_list)):
        example_name, description_opt, id_num = demo_config_list[i].split(',')

        with open(f"./outputs/robotouille/code/spec2code/{prompt_version}/spec2code_{example_name}_{description_opt}_main_code.txt", "r") as fin:
            cap_full_code = fin.read()

        with open(f"./outputs/robotouille/code/{lmp_name}/{prompt_version}/{lmp_name}_{example_name}_{description_opt}_main_code.txt", "r") as fin:
            lmp_code = fin.read()

        result = compute_bleu_score_for_code(cap_full_code, lmp_code)

        if description_opt == "none-specific":
            description_opt = "none"

        key = f"{example_name},{description_opt}"
        
        if key not in result_dict:
            result_dict[key] = []

        result_dict[key].append(result)

    return result_dict

def extract_final_states(state_str):
    """
    Given a state string, return a list of all the predicates and their values at the end of the state trajectory
    """
    state_str_b4_init, _, _  = state_str.partition("<init-state>")
    
    state_str_list = state_str_b4_init.split("<state-")[1:]

    # accumulate a list of all the predicates that have changed and their final value
    final_predicates_dict = {}
    for state_str_raw in state_str_list:
        _, _, state_str = state_str_raw.partition(">\n")
        state_str, _, _ = state_str.partition("\n\n")

        # get the list of predicates
        predicate_list = state_str.split("\n")

        for pred in predicate_list:
            if pred != "":
                pred_split = pred.split("):")
                key = pred_split[0] + ")"
                value = pred_split[-1]
                # if key already exists, this will overwrite the previous state's value
                final_predicates_dict[key] = value

    return [f"{key}:{final_predicates_dict[key]}" for key in final_predicates_dict]


def combine_all_states(state_str):
    state_str_b4_init, _, _  = state_str.partition("<init-state>")

    state_str_list = state_str_b4_init.split("<state-")[1:]

    total_predicate_list = []
    
    for state_str_raw in state_str_list:
        _, _, state_str = state_str_raw.partition(">\n")
        state_str, _, _ = state_str.partition("\n\n")

        # get the list of predicates
        predicate_list = state_str.split("\n")

        total_predicate_list.extend(predicate_list)

    return total_predicate_list


def unit_test(state_str, unit_test_list, 
              target_obj_list, target_loc_list, target_obj_loc_list):
    """
    General unit test used for examples that can be tested just by examining the final state

    Return 0 for satisfying the unit test, 1 for not satisfying it
    """
    final_predicates_list = extract_final_states(state_str)

    success = 1
    
    for test in unit_test_list:
        for i in range(len(target_obj_list)):
            obj_name = target_obj_list[i]
            keyword_to_replace = f"<obj_{i + 1}>"

            # replacing the placeholder with the correct object name
            test = test.replace(keyword_to_replace, obj_name)
        
        for i in range(len(target_loc_list)):
            loc_name = target_loc_list[i]
            keyword_to_replace = f"<p-loc_{i + 1}>"

            # replacing the placeholder with the correct object name
            test = test.replace(keyword_to_replace, loc_name)

        for i in range(len(target_obj_loc_list)):
            loc_name = target_obj_loc_list[i]
            keyword_to_replace = f"<o-loc_{i + 1}>"

            # replacing the placeholder with the correct object name
            test = test.replace(keyword_to_replace, loc_name)

        if test not in final_predicates_list:
            success = 0

            break

    return success


def flatten_order_req_list(order_req_list):
    """
    Because the order requirement list sometimes contain partially ordered predicates, represented as tuples,
        when we flatten the order_req_list, we also keep track of the index of predicates that are unordered with respect to each other
    """
    flat_list = []

    unordered_group_list = []
    
    i = 0
    for req in order_req_list:
        if type(req) == str:
            flat_list.append(req)
            i += 1
        else:
            unordered_group_list.append([])
            for r in req:
                flat_list.append(r)
                unordered_group_list[-1].append(i)
                i += 1

    return flat_list, unordered_group_list


def can_be_unordered(i, j, unordered_group_list):
    for group in unordered_group_list:
        if i in group and j in group:
            return True
        
    return False

def unit_test_on_order(total_predicate_list_in, order_req_list):
    total_predicate_list = deepcopy(total_predicate_list_in)

    flat_order_req_list, unordered_group_list = flatten_order_req_list(order_req_list)

    order_pred_index_list = []

    item_dict = {}

    for i in range(len(flat_order_req_list)):
        pred_template = flat_order_req_list[i]

        if "<" in pred_template:
            for j in range(i):
                if f"<{j}>" in pred_template:
                    pred_template = pred_template.replace(f"<{j}>", item_dict[j])

        re_compile = re.compile(pred_template)

        match_result = list(filter(re_compile.match, total_predicate_list))

        if len(match_result) != 0:
            # because total_predicate_list is sequential (early states in the front)
            #   we use the first match result
            matched = match_result[0]

            # keep track of the index of the matched item
            #   smaller index means that this predicate happened earlier
            order_pred_index_list.append(total_predicate_list.index(matched))

            try:
                # sometimes we need the item id for subsequent predicates
                #   so we keep track of it in the item_dict
                item_dict[i] = re_compile.search(matched).group(1)
            except:
                pass

            # because we have used matched, we remove it
            total_predicate_list.remove(matched)
        else:
            return False

    # sort the indices from small to large (then get the sort indices)
    #   if the indices fully match order_req_list, it should go from 0 to len(order_req_list) - 1
    order_index_list = list(np.argsort(order_pred_index_list))
    
    if order_index_list != list(range(len(order_index_list))):
        # the order of predicates that occurred doesn't fully match order_req_list
        for i in range(len(order_index_list)):
            idx = order_index_list[i]
            # if doesn't match i, see if i and idx below in the same unordered group
            if i != idx:
                if not can_be_unordered(i, idx, unordered_group_list):
                    print(f"{i} and {idx} cannot be unordered")
                    return False

    return True


def high_level_unit_test(state_str, order_req_list):
    total_predicate_list = combine_all_states(state_str)

    has_correct_order = unit_test_on_order(total_predicate_list, order_req_list)

    return int(has_correct_order)


def unit_test_eval(lmp_name, prompt_version, demo_config_filename):
    """
    Given a query config, run unit test on all the examples for a model
    
    Return:
        a dictionary where the key is "{example_name},{description_opt}" and the value is the token comparison score for 
        each example that fits in the category
    """
    with open(f"./data/robotouille/demonstration_config/{demo_config_filename}.txt", "r") as fin:
        demo_config_list = fin.read().splitlines()
    
    result_dict = {}

    for i in range(len(demo_config_list)):
        print(f"{lmp_name}_{demo_config_list[i]}")

        example_name, description_opt, id_num = demo_config_list[i].split(',')

        # print(f"Running unit test on {lmp_name}_{example_name}_{description_opt}...")

        with open(f"./outputs/robotouille/state/{lmp_name}/{prompt_version}/{lmp_name}_{example_name}_{description_opt}_{id_num}_state.txt", "r") as fin:
            state_str = fin.read()

        with open(f"./outputs/robotouille/query/{lmp_name}/env-info/{prompt_version}/{lmp_name}_{example_name}_{description_opt}_{id_num}_env-info.txt", "r") as fin:
            env_info_list = fin.read().splitlines()
        
        total_obj_list, target_obj_list, total_loc_list, target_loc_list, target_obj_loc_list = [convert_str_to_list(l) for l in env_info_list]
    
        if description_opt == "none-specific":
            # so that we can properly get the unit test
            description_opt = "none"
        
        if "high-level" in example_name:
            result = high_level_unit_test(state_str,
                                            order_req_list=robotouille_prompt_template[example_name]['unit_tests'][description_opt])
        else:
            result = unit_test(state_str, 
                        unit_test_list = robotouille_prompt_template[example_name]['unit_tests'][description_opt], 
                        target_obj_list = target_obj_list,
                        target_loc_list = target_loc_list, 
                        target_obj_loc_list = target_obj_loc_list)
            

        key = f"{example_name},{description_opt}"
        
        if key not in result_dict:
            result_dict[key] = []

        result_dict[key].append(result)

    return result_dict



def robotouille_overall_eval(model_list, demo_version):
    """
    Given a query config, run (1) execution success (2) unit test and (3) token-wise comparision on all the examples for all models
    
    Save the results in two .csv
        _overall-results.csv
            take average of the result based on each task
        _specific-results.csv
            take average of the result based on each task's each specific requirement
    """
    with open(f"./data/robotouille/prompt/demo2code/demo2code_prompt.yaml", "r") as f:
        prompt_dict = yaml.safe_load(f)

    prompt_version = prompt_dict["prompt_version"].strip()

    demo_config_filename = f"{demo_version}-test-time_demo-config"
    with open(f"./data/robotouille/demonstration_config/{demo_config_filename}.txt", "r") as fin:
        demo_config_list = fin.read().splitlines()

    demo_config_dict = {}

    # keep track of the specific requirements associated with a task
    for demo_config in demo_config_list:
        example_name, description_opt, _ = demo_config.split(',')
        
        if example_name not in demo_config_dict:
            demo_config_dict[example_name] = []

        if description_opt not in demo_config_dict[example_name]:
            demo_config_dict[example_name].append(description_opt)

    total_unique_setting = 0
    for key in demo_config_dict:
        total_unique_setting += len(demo_config_dict[key])

    e_dict = {}
    for model in model_list:
        with open(f"./outputs/robotouille/eval_result/{model}/{model}_{prompt_version}_exec-status.json", "r") as fin:
            e_dict[model] = extract_exec_result(json.load(fin), demo_config_list)

    u_dict = {}
    for model in model_list:
        u_dict[model] = unit_test_eval(model, prompt_version, demo_config_filename=demo_config_filename)
    
    t_dict = {}
    for model in model_list:
        t_dict[model] = bleu_eval(model, prompt_version, demo_config_filename=demo_config_filename)

    with open(f"./outputs/robotouille/eval_result/overall/{prompt_version}_specific-results.csv", "w") as fout:
        fout.write("overall-task-name,specific-requirement,models,avg-exec-success-pct,avg-unit-test-success-pct,avg-token-comparison-score\n")

        for example_name in demo_config_dict:
            for description_opt in demo_config_dict[example_name]:
                if description_opt == "none-specific":
                    description_opt = "none"
                key = f"{example_name},{description_opt}"
                
                for model in model_list:
                    avg_exec_success = np.mean(e_dict[model][key])
                    avg_unit_test_success = np.mean(u_dict[model][key])
                    avg_token_success = np.mean(t_dict[model][key])
                    fout.write(f"{example_name},{description_opt},{model},{avg_exec_success},{avg_unit_test_success},{avg_token_success}\n")

    with open(f"./outputs/robotouille/eval_result/overall/{prompt_version}_overall-results.csv", "w") as fout:
        fout.write("overall-task-name,models,avg-exec-success-pct,avg-unit-test-success-pct,avg-token-comparison-score\n")

        for example_name in demo_config_dict:
            for model in model_list:
                exec_success_list = []
                unit_test_list = []
                token_test_list = []

                for description_opt in demo_config_dict[example_name]:
                    if description_opt == "none-specific":
                        description_opt = "none"
                    key = f"{example_name},{description_opt}"
                    exec_success_list.extend(e_dict[model][key])
                    unit_test_list.extend(u_dict[model][key])
                    token_test_list.extend(t_dict[model][key])

                avg_exec_success = np.mean(exec_success_list)
                avg_unit_test_success = np.mean(unit_test_list)
                avg_token_success = np.mean(token_test_list)

                fout.write(f"{example_name},{model},{avg_exec_success},{avg_unit_test_success},{avg_token_success}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--demo_version", type=str, default="latest")
    parser.add_argument(
        '--model_names', 
        choices=['spec2code', 'lang2code', 'demonolang2code', 'demo2code'], 
        nargs='+', 
        default=['spec2code', 'lang2code', 'demonolang2code', 'demo2code'],
        help="names of the lmps to execute"
    ) # example --model_names spec2code lang2code demonolang2code demo2code
    args = parser.parse_args()

    robotouille_overall_eval(args.model_names, args.demo_version)

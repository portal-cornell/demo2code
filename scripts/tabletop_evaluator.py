import numpy as np
import json
import yaml
import argparse
import re

from scripts.overall_helpers.utils import *
from scripts.overall_helpers.eval_helper import compute_bleu_score_for_code, extract_exec_result

from scripts.tabletop_helpers.tabletop_template import prompt_template

"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    BLEU evaluation

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""
def bleu_eval(model_name, prompt_version, demo_config_filename):
    """
    Given a query config, compute BLEU score between the oracle code (spec2code) and the current model's code

    Parameters:
        model_name (str): one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        prompt_version (str) : the version of {model_name}'s prompt
            this specifies where the generated code is
        demo_config_filename (str): the filename of the demonstration configuration file
            
    Return:
        a dictionary where the key is "{example_name},{description_opt}" and the value is the BLEU score for 
        each example that fits in the category
    """
    with open(f"./data/tabletop/demonstration_config/{demo_config_filename}.txt", "r") as fin:
        demo_config_list = fin.read().splitlines()

    result_dict = {}

    for i in range(len(demo_config_list)):
        example_name, description_opt, id_num = demo_config_list[i].split(',')

        with open(f"./outputs/tabletop/code/spec2code/{prompt_version}/spec2code_{example_name}_{description_opt}_{id_num}_code.txt", "r") as fin:
            cap_full_code = fin.read()

        with open(f"./outputs/tabletop/code/{model_name}/{prompt_version}/{model_name}_{example_name}_{description_opt}_{id_num}_code.txt", "r") as fin:
            lmp_code = fin.read()

        result = compute_bleu_score_for_code(cap_full_code, lmp_code)

        if description_opt == "none-specific":
            description_opt = "none"

        key = f"{example_name},{description_opt}"
        
        if key not in result_dict:
            result_dict[key] = []

        result_dict[key].append(result)

    return result_dict


"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Unit test evaluation (Unit Test Pass Rate)

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""
def unit_test_eval(model_name, prompt_version, demo_config_filename, obj_lists_used_path):
    """
    Given a query config, run unit test on all the examples for a model

    Parameters:
        model_name (str): one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        prompt_version (str) : the version of {model_name}'s prompt
            this specifies where the generated code is
        demo_config_filename (str): the filename of the demonstration configuration file
        obj_lists_used_path (str): the complete filepath to the file that stores the object lists used for each task
    
    Return:
        a dictionary where the key is "{example_name},{description_opt}" and the value is the token comparison score for 
        each example that fits in the category
    """
    with open(f"./data/tabletop/demonstration_config/{demo_config_filename}.txt", "r") as fin:
        demo_config_list = fin.read().splitlines()

    with open(obj_lists_used_path, "r") as fin:
        obj_lists_to_use_str = fin.read().splitlines()
    
    result_dict = {}

    for i in range(len(demo_config_list)):
        example_name, description_opt, id_num = demo_config_list[i].split(',')

        if model_name == "spec2code":
            if description_opt == "none-specific":
                # so that we can properly get the unit test
                description_opt = "none"

            key = f"{example_name},{description_opt}"
        
            if key not in result_dict:
                result_dict[key] = []

            result_dict[key].append(1)
            continue

        obj_list = convert_str_to_list(obj_lists_to_use_str[2 * i])
        active_obj_list = convert_str_to_list(obj_lists_to_use_str[2 * i + 1])

        if example_name == "place-at-corner" or example_name == "place-at-edge" or "stack-all-type" in example_name:
            inactive_obj_list = [obj for obj in obj_list if obj not in active_obj_list]
        else:
            # the second object in the active object list should not be moved
            inactive_obj_list = [obj for obj in obj_list if obj not in active_obj_list] + [active_obj_list[1]]

        with open(f"./outputs/tabletop/state/{model_name}/{prompt_version}/{model_name}_{example_name}_{description_opt}_{id_num}_state.txt", "r") as fin:
            state_str = fin.read()

        if description_opt == "none-specific":
            # so that we can properly get the unit test
            description_opt = "none"
        
        if "stack-all-type-order" in example_name:
            # determine the number of objects that are numbered
            if description_opt == "none":
                num_of_ordered = -1
            elif description_opt == "fully-ordered":
                num_of_ordered = len(active_obj_list)
            else:
                num_of_ordered = int(description_opt[-1])

            result = stack_all_type_order_unit_test(state_str,
                                                    active_obj_list,
                                                    inactive_obj_list,
                                                    num_of_ordered)
                
        elif "stack-all-type" in example_name:
            if description_opt == "none":
                max_stack_height = np.inf
            else:
                max_stack_height = int(description_opt[-1])

            result = stack_all_type_unit_test(state_str, 
                                              active_obj_list=active_obj_list, 
                                              inactive_obj_list=inactive_obj_list,
                                              max_stack_height=max_stack_height)
        elif example_name == "stack-all-objects":
            result = stack_all_objects_unit_test(state_str, 
                                              active_obj_list=active_obj_list,
                                              categorized=description_opt == "categorized")
        else:
            result = unit_test(state_str, 
                        unit_test_list = prompt_template[example_name]['unit_tests'][description_opt], 
                        active_obj_list = active_obj_list,
                        inactive_obj_list = inactive_obj_list)

        key = f"{example_name},{description_opt}"
        
        if key not in result_dict:
            result_dict[key] = []

        result_dict[key].append(result)

    return result_dict


def unit_test(state_str, unit_test_list, active_obj_list, inactive_obj_list):
    """
    General unit test used for examples that can be tested just by examining the final state

    Parameter:
        state_str (str) state trajectory string
        unit_test_list (list) list of all the unit tests
        active_obj_list (list) list of objects that are actively relevant for the task
        inactive_obj_list (list) list of objects that should not be moved during the task because they are not relevant

    Return 0 for satisfying the unit test, 1 for not satisfying it
    """
    final_predicates_list = extract_final_states(state_str)

    success = 1

    # inactive objects should not move
    invalid_predicates_list = [f"has_moved:{obj}:1" for obj in inactive_obj_list]
    for invalid_pred in invalid_predicates_list:
        if invalid_pred in final_predicates_list:
            success = 0
            return success
    
    # these predicates in the unit_test_list should appear in the final predicate list
    for test in unit_test_list:
        for i in range(len(active_obj_list)):
            obj_name = active_obj_list[i]
            keyword_to_replace = f"<obj_{i + 1}>"

            # replacing the placeholder with the correct object name
            test = test.replace(keyword_to_replace, obj_name)

        if test not in final_predicates_list:
            success = 0
            break

    return success



def stack_all_type_unit_test(state_str, active_obj_list, inactive_obj_list, max_stack_height):
    """
    Unit test used for 'stack all blocks/cylinders' task where the height of the stack matters
    
    Parameter:
        state_str (str) state trajectory string
        active_obj_list (list) list of objects that are actively relevant for the task
        inactive_obj_list (list) list of objects that should not be moved during the task because they are not relevant
        max_stack_height (int) maximum heigh for a stack

    Return 0 for satisfying the unit test, 1 for not satisfying it
    """
    final_predicates_list = extract_final_states(state_str)

    success = 1

    # inactive objects should not move
    invalid_predicates_list = [f"has_moved:{obj}:1" for obj in inactive_obj_list]
    for invalid_pred in invalid_predicates_list:
        if invalid_pred in final_predicates_list:
            success = 0
            return success
        
    items_has_moved = [pred.split(":")[1].split(",")[0] for pred in final_predicates_list if "on_top_of" in pred and "table:0" in pred]

    items_not_moved = [item for item in active_obj_list if item not in items_has_moved]

    placement_dict = {item: [] for item in items_not_moved}

    # determine the stacks created based on the state trajectory
    for pred in final_predicates_list:
        if "on_top_of" in pred and "table" not in pred and pred[-1] == "1":
            _, active_objs, _ = pred.split(":")
            obj_1, obj_2 = active_objs.split(",")
            if obj_2 in items_not_moved:
                placement_dict[obj_2].append(obj_1)

    # talculate the height of each stack
    # make sure each stack satisifies the height
    stack_height = [len(placement_dict[base_obj]) + 1 for base_obj in placement_dict]

    # make sure all the items have been stacked
    all_items_stacked = np.sum(stack_height) == len(active_obj_list)
    # make sure each stack satisifies the height
    height_limit_satisfied = np.sum([h <= max_stack_height for h in stack_height]) == len(stack_height)

    if len(stack_height) == 1:
        # if there's only one stack, assume the stacking is optimal
        optimal_stacking = True
    else:
        # all stacks except the last one must be fully stacked (equal to the maximum stack height)
        optimal_stacking = np.sum([h == max_stack_height for h in stack_height[:-1]]) == (len(stack_height) - 1)
    
    return int(all_items_stacked and height_limit_satisfied and optimal_stacking)



def stack_all_type_order_unit_test(state_str, active_obj_list, inactive_obj_list, num_of_ordered):
    """
    Unit test used for 'stack all blocks/cylinders into one stack' task where the order of objects matters
    
    Parameter:
        state_str (str) state trajectory string
        active_obj_list (list) list of objects that are actively relevant for the task
        inactive_obj_list (list) list of objects that should not be moved during the task because they are not relevant
        num_of_ordered (int) number of objects that should be ordered
            if it's -1, order doesn't matter

    Return 0 for satisfying the unit test, 1 for not satisfying it
    """
    final_predicates_list = extract_final_states(state_str)

    success = 1

    # inactive objects should not move
    invalid_predicates_list = [f"has_moved:{obj}:1" for obj in inactive_obj_list]
    for invalid_pred in invalid_predicates_list:
        if invalid_pred in final_predicates_list:
            success = 0
            return success
    
    # use helper function to extract the stacks created based on the state trajectories
    obj_stacking_order_dict = extract_obj_stacking_order(state_str)

    if len(obj_stacking_order_dict) != 1:
        # unable to find just one stack
        return int(False)
    
    # because there's only 1 stack, we can just get the first stack's order
    obj_stacking_order = obj_stacking_order_dict[1]

    obj_type_name = active_obj_list[0].split()[-1]
    # first verify that
    #   it only stacked objects that match 1 type
    #   it didn't stack more objects than needed
    stacked_all_type = all(obj_type_name in obj_name for obj_name in obj_stacking_order) and len(obj_stacking_order) == len(active_obj_list)

    if not stacked_all_type:
        # failed, no need to check the rest
        return int(False)

    if num_of_ordered != -1:
        # some objects must be stacked in a certain order
        must_match = active_obj_list[:num_of_ordered]

        found_match = False
        for i in range(len(obj_stacking_order) - num_of_ordered + 1):
            sublist = obj_stacking_order[i:i+num_of_ordered]

            if sublist == must_match:
                found_match = True
                break

        return int(found_match)
    else:
        # when the order doesn't count, just making sure that all the types are stacked
        return int(stacked_all_type)


def stack_all_objects_unit_test(state_str, active_obj_list, categorized=False):
    """
    Unit test used for 'stack all objects' task where the objects might need to be sorted based on type into different stacks
    
    Parameter:
        state_str (str) state trajectory string
        active_obj_list (list) list of objects that are actively relevant for the task
        categorized (bool) True if the objects need to be sorted based on type into different stacks

    Return 0 for satisfying the unit test, 1 for not satisfying it
    """
    # use helper function to extract the stacks created based on the state trajectories
    obj_stacking_order_dict = extract_obj_stacking_order(state_str)

    if len(obj_stacking_order_dict) != 2:
        # not able to find 2 stacks
        return int(False)
    
    num_objects_stacked = len(obj_stacking_order_dict[1]) + len(obj_stacking_order_dict[2])

    if num_objects_stacked != len(active_obj_list):
        # did not stack all objects
        return int(False)
    
    if categorized:
        # one stack must be all blocks and one stack must be all cylinders
        stack_1_all_blocks = all(["block" in obj_name for obj_name in obj_stacking_order_dict[1]])
        stack_1_all_cylinders = all(["cylinder" in obj_name for obj_name in obj_stacking_order_dict[1]])

        stack_2_all_blocks = all(["block" in obj_name for obj_name in obj_stacking_order_dict[2]])
        stack_2_all_cylinders = all(["cylinder" in obj_name for obj_name in obj_stacking_order_dict[2]])

        return int((stack_1_all_blocks and stack_2_all_cylinders) or (stack_1_all_cylinders and stack_2_all_blocks))
    else:
        # nothing else to check, success
        return int(True)

"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Unit test evaluation helpers

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""

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
            pred_split = pred.split(":")
            key = ":".join(pred_split[:-1])
            value = pred_split[-1]
            # if key already exists, this will overwrite the previous state's value
            final_predicates_dict[key] = value

    return [f"{key}:{final_predicates_dict[key]}" for key in final_predicates_dict]


def extract_obj_stacking_order(state_trans_str):
    """
    Extract the stacks that got created through the state trajectory
        The key is int (1 = 1st stack, 2 = 2nd stack, etc)
        The value is the list of object in that stack from bottom to top
    """
    if state_trans_str == "<init-state>\n":
        return {}

    state_str_b4_init, _, _  = state_trans_str.partition("<init-state>")
    
    state_str_list = state_str_b4_init.split("<state-")[1:]

    stack_from_bottom_to_top = {1:[]}
    stack_num = 1

    for i in range(len(state_str_list)):
        state_str_raw = state_str_list[i]

        _, _, state_str = state_str_raw.partition(">\n")
        state_str, _, _ = state_str.partition("\n\n")

        # get the list of predicates
        predicate_list = state_str.split("\n")

        # step 1: find the objects that had moved
        not_on_table_r = re.compile(r"on_top_of:(.*),table:0")
        not_on_table_match_list = list(filter(not_on_table_r.match, predicate_list))
        not_on_table_active_obj_list = [not_on_table_r.search(s).group(1) for s in not_on_table_match_list]

        moved_r = re.compile(r"has_moved:(.*):1")
        moved_match_list = list(filter(moved_r.match, predicate_list))
        moved_active_obj_list = [moved_r.search(s).group(1) for s in moved_match_list]

        active_obj_list = list(set(not_on_table_active_obj_list).intersection(set(moved_active_obj_list)))
        
        if len(active_obj_list) == 1:
            active_obj = active_obj_list[0]
        elif len(active_obj_list) == 0 and \
                    len(not_on_table_active_obj_list) == 0 and len(moved_active_obj_list) == 1:
            # Assume that this is the block to get placed on
            active_obj = moved_active_obj_list[0]

            if stack_from_bottom_to_top[stack_num] != []:
                stack_num += 1

            stack_from_bottom_to_top[stack_num] = [active_obj]
            continue

        elif len(active_obj_list) == 0 and \
                    len(not_on_table_active_obj_list) == 1 and len(moved_active_obj_list) == 0:
            active_obj = not_on_table_active_obj_list[0]
        elif len(active_obj_list) == 0 and len(not_on_table_active_obj_list) == 0 and len(moved_active_obj_list) == 0:
            return {}
        else:
            assert False

        # step 2: find the bottom obj that the active object is placed on top of
        on_top_r = re.compile(f"on_top_of:{active_obj},(.*):1")
        on_top_match_list = list(filter(on_top_r.match, predicate_list))
        bottom_obj_list = [on_top_r.search(s).group(1) for s in on_top_match_list]

        if stack_from_bottom_to_top[stack_num] == []:
            for bottom_obj in bottom_obj_list:
                if bottom_obj not in stack_from_bottom_to_top[stack_num]:
                    stack_from_bottom_to_top[stack_num].append(bottom_obj)

        stack_from_bottom_to_top[stack_num].append(active_obj)

    return stack_from_bottom_to_top


"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Main function

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""

def tabletop_overall_eval(demo_config_filename, obj_lists_used_path):
    """
    Given a demonstration config, run 
        (1) execution success 
        (2) unit test
        (3) BLEU score
    on all the examples for all models
    
    Save the results in two .csv
        _overall-results.csv
            take average of the result based on each task
        _specific-results.csv
            take average of the result based on each task's each specific requirement

    Parameters:
        model_name (str): one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        demo_config_filename (str): the filename of the demonstration configuration file
        obj_lists_used_path (str): the complete filepath to the file that stores the object lists used for each task
    """
    with open(f"./data/tabletop/prompt/demo2code/demo2code_prompt.yaml", "r") as f:
        prompt_dict = yaml.safe_load(f)

    prompt_version = prompt_dict["prompt_version"].strip()

    with open(f"./data/tabletop/demonstration_config/{demo_config_filename}.txt", "r") as fin:
        demo_config_list = fin.read().splitlines()

    demo_config_dict = {}

    for demo_config in demo_config_list:
        example_name, description_opt, _ = demo_config.split(',')
        
        if example_name not in demo_config_dict:
            demo_config_dict[example_name] = []

        if description_opt not in demo_config_dict[example_name]:
            demo_config_dict[example_name].append(description_opt)

    total_unique_setting = 0
    for key in demo_config_dict:
        total_unique_setting += len(demo_config_dict[key])

    model_list = ["spec2code", "lang2code", "demonolang2code", "demo2code"]

    e_dict = {}

    for model in model_list:
        with open(f"./outputs/tabletop/eval_result/{model}/{model}_{prompt_version}_exec-status.json", "r") as fin:
            e_dict[model] = extract_exec_result(json.load(fin), demo_config_list)

    u_dict = {}
    for model in model_list:
        u_dict[model] = unit_test_eval(model, prompt_version, demo_config_filename=demo_config_filename, 
                                    obj_lists_used_path=obj_lists_used_path)
    
    t_dict = {}
    for model in model_list[1:]:
        t_dict[model] = bleu_eval(model, prompt_version, demo_config_filename=demo_config_filename)

    with open(f"./outputs/tabletop/eval_result/overall/{prompt_version}_specific-results.csv", "w") as fout:
        fout.write("overall-task-name,specific-requirement,models,avg-exec-success-pct,avg-unit-test-success-pct,avg-token-comparision-score\n")

        for example_name in demo_config_dict:
            for description_opt in demo_config_dict[example_name]:   
                if description_opt == "none-specific":
                    description_opt = "none"
                key = f"{example_name},{description_opt}"
                
                for model in model_list:
                    avg_exec_success = np.mean(e_dict[model][key])
                    avg_unit_test_success = np.mean(u_dict[model][key])

                    if model == "spec2code":
                        avg_token_success = 1.0
                    else:
                        avg_token_success = np.mean(t_dict[model][key])

                    fout.write(f"{example_name},{description_opt},{model},{avg_exec_success},{avg_unit_test_success},{avg_token_success}\n")

    with open(f"./outputs/tabletop/eval_result/overall/{prompt_version}_overall-results.csv", "w") as fout:
        fout.write("overall-task-name,models,avg-exec-success-pct,avg-unit-test-success-pct,avg-token-comparision-score\n")

        for example_name in demo_config_dict:
            for model in model_list:
                avg_exec_success = np.mean(e_dict[model][key])

                unit_test_list = []
                token_test_list = []

                for description_opt in demo_config_dict[example_name]:
                    # exclude the random from the unit test result
                    if description_opt != "none-specific":
                        key = f"{example_name},{description_opt}"

                        unit_test_list.extend(u_dict[model][key])

                        if model != "spec2code":
                            token_test_list.extend(t_dict[model][key])

                avg_unit_test_success = np.mean(unit_test_list)

                if model != "spec2code":
                    avg_token_success = np.mean(token_test_list)
                else:
                    avg_token_success = 1.0

                fout.write(f"{example_name},{model},{avg_exec_success},{avg_unit_test_success},{avg_token_success}\n")
  

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the generated code for tabletop env")
    parser.add_argument("--demo_version", type=str, default="latest")
    args = parser.parse_args()

    tabletop_overall_eval(f"{args.demo_version}_query-config", 
                          f"./data/tabletop/demonstration_config/{args.demo_version}_query-obj-lists-used.txt")
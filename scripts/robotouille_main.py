"""
After the code has been generated for a particular model, this file is used to execute the code. Under query and configs,
modify the file named MM_DD-demo_config for the current date. In this file, add each of the examples and tasks as 
"<example-name>,<task-name>,<id>" where id is a number that is unique to each example-task pair. We recommend using 10 ids
for each example-task pair for robustness.
"""

import numpy as np
import os
import traceback
import json
import yaml
import argparse

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.overall_helpers.model_config_all import model_cfg_all
from scripts.overall_helpers.utils import safe_mkdir
from scripts.overall_helpers.lmp import LMP, LMPFGen

from scripts.robotouille_helpers.robotouille_API import RobotouilleAPI

from robotouille.robotouille_env import create_robotouille_env

"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Helpfer functions

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""

def execute_code_for_one_demo(model_name, code_base_name, result_base_name, prompt_version, 
                              save_state_base_name = "", render=True):
    """
    Execute the code generated for one set of demos. 

    Parameters:
        model_name (str) - one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        code_base_name (str) - in the format of {model_name}_{example_name}_{description_opt}_main
            this specifies the corresponding code to execute
        result_base_name (str) - in the format of {model_name}_{example_name}_{description_opt}_{id_num}
            this specifies the base name of where the result will get stored
        prompt_version (str) - the version of {model_name}'s prompt
            this specifies where the generated code is
        save_state_base_name (str) - filename of where the state trajectory should be saved

        Rendering parameters:
            render (bool) - True if the env should be rendered
    """
    print(f"Executing ROBOTOUILLE code generated for query={result_base_name}_query.txt")

    model_name, example_name, description_opt, id_num = result_base_name.split("_")

    if save_state_base_name == "":
        state_save_path = f"./outputs/robotouille/state/{model_name}/{prompt_version}/{result_base_name}_state.txt"
    else:
        state_save_path = f"./outputs/robotouille/state/{model_name}/{prompt_version}/{save_state_base_name}_state.txt"

    save_env_info_path = f"./outputs/robotouille/env-info/{model_name}/{prompt_version}/{result_base_name}_env-info.txt"

    exec_status = -1
    while exec_status == -1:
        env, lmp_robotouille_ui = init_env_lmp(model_name, 
                                            prompt_version,
                                            state_save_path,
                                            save_env_info_path,
                                            example_name,
                                            id_num,
                                            render=render)
        
        try:
            exec_status = lmp_robotouille_ui(user_query='', 
                                             context='', 
                                             load_code_path = f"./outputs/robotouille/code/{model_name}/{prompt_version}/{code_base_name}_code.txt")
        except Exception as e:
            traceback.print_exc()
            exec_status = 0
        
    env.log_init_predicates()

    return exec_status


def execute_code_based_on_demo_config(model_name, demo_version, render=True):
    """
    Execute all the code specified by the demo config file stored at 'data/robotouille/demonstration_config/{demo_version}-test-time_demo-config.txt'
        the code are loaded based on the prompt_version in the 'data/robotouille/prompt/{model_name}/{model_name}_prompt.yaml' file
            code is stored in 'outputs/robotouille/code/{model_name}/{demo_version}' folder
    
    Parameters:
        model_name (str) - one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        demo_version (str): this correspond to the version of demonstrations that will get used

        Rendering parameters:
            render (bool) - True if the env should be rendered
    """
    with open(f"./data/robotouille/prompt/{model_name}/{model_name}_prompt.yaml", "r") as f:
        prompt_dict = yaml.safe_load(f)

    prompt_version = prompt_dict["prompt_version"].strip()

    # make the directory to store the states
    safe_mkdir(f"./outputs/robotouille/state/{model_name}/{prompt_version}")
    safe_mkdir(f"./data/robotouille/demonstration/{model_name}/{prompt_version}")
    # Create the env-info directory in case it doesn't exist
    safe_mkdir(f"./outputs/robotouille/env-info/")
    safe_mkdir(f"./outputs/robotouille/env-info/{model_name}")
    safe_mkdir(f"./outputs/robotouille/env-info/{model_name}/{prompt_version}")
    safe_mkdir(f"./outputs/robotouille/code/helper-functions/{prompt_version}")

    demo_config_filename = f"{demo_version}-test-time_demo-config"
    with open(f"./data/robotouille/demonstration_config/{demo_config_filename}.txt", "r") as fin:
        demo_config_list = fin.read().splitlines()

    # where to store the execution status (whether the code successfully executes without any runtime error)
    exec_status_json_fp = f"./outputs/robotouille/eval_result/{model_name}/{model_name}_{prompt_version}_exec-status.json"
    if not os.path.isfile(exec_status_json_fp):
        # initialize the exec_status_dict
        exec_status_dict = {}
    else:
        with open(exec_status_json_fp, "r") as fin:
            exec_status_dict = json.load(fin)

    for i in range(len(demo_config_list)):
        example_name, description_opt, id_num = demo_config_list[i].split(',')
        
        code_base_name = f"{model_name}_{example_name}_{description_opt}_main"  # base name to load the code
        result_base_name = f"{model_name}_{example_name}_{description_opt}_{id_num}"  # base name to save the results

        if not os.path.isfile(f"./outputs/robotouille/state/{model_name}/{prompt_version}/{result_base_name}_state.txt"):
            exec_result = execute_code_for_one_demo(model_name, 
                                                    code_base_name, result_base_name, 
                                                    prompt_version, render=render)

            if example_name not in exec_status_dict:
                exec_status_dict[example_name] = {}

            if description_opt not in exec_status_dict[example_name]:
                exec_status_dict[example_name][description_opt] = {}
            
            exec_status_dict[example_name][description_opt][id_num] = exec_result

            with open(exec_status_json_fp, "w") as fout:
                fout.write(json.dumps(exec_status_dict, indent=4))


def init_env_lmp(model_name, 
                    prompt_version, state_save_path, save_env_info_path,
                    example_name, id_num,
                    render=True):
    # make sure the env name matches robotouille's env
    # (https://github.com/portal-cornell/robotouille/tree/main/environments/env_generator/examples)
    env_name = "_".join(example_name.split("-"))
    
    env, env_json, renderer = create_robotouille_env(env_name, seed=id_num, noisy_randomization=True)

    # load the base prompt based on the the prompt file specified in the configuration
    model_cfg = model_cfg_all[model_name]

    LMP_env = RobotouilleAPI(env, env_json, state_save_path, render)
    LMP_env.reset()

    # define all the APIs that the LLM's code will be able to use
    fixed_vars = {
        'np': np
    }

    api_vars = {
        k: getattr(LMP_env, k)
        for k in [
            'move', 'basic_move', 'pick_up', 'pick', # pick is an alias of pick_up
            'place', 'cut', 'noop', 'stack', 'unstack', 'start_cooking',
            'is_cut', 'is_cooked',
            'is_holding',
            'is_in_a_stack', 'get_obj_that_is_underneath',
            'get_obj_location', 'get_curr_location',
            'get_all_obj_names_that_match_type', 'get_all_location_names_that_match_type'
        ]
    }

    # creating the function-generating LMP
    lmp_fgen = LMPFGen(model_name, prompt_version, fixed_vars, api_vars)

    # creating the LMP that deals w/ high-level language commands
    lmp_high_level = LMP(
        model_name, model_cfg, fixed_vars, api_vars, lmp_fgen, return_exec_status=True
    )

    # save the env information for eval later
    total_obj_list = LMP_env.get_all_objects()
    total_loc_list = LMP_env.get_all_locations()
    target_obj_list = [None, None] # At most 2 target objects
    for item in env_json["items"]:
        if item.get('id'):
            if item["id"] == "a": target_obj_list[0] = item['name']
            elif item["id"] == "b": target_obj_list[1] = item['name']
            else: raise ValueError("Invalid item id")
    target_obj_loc_list = []
    for obj in target_obj_list:
        target_obj_loc_list.append(LMP_env.get_obj_location(obj))
    target_loc_list = [None, None]
    for station in env_json["stations"]:
        total_loc_list.append(station['name'])
        if station.get('id'):
            if station["id"] == "A": target_loc_list[0] = station['name']
            elif station["id"] == "B": target_loc_list[1] = station['name']
            else: raise ValueError("Invalid station id")

    with open(save_env_info_path, "w") as fout:
        fout.write(f"{total_obj_list}\n")
        fout.write(f"{target_obj_list}\n")
        fout.write(f"{total_loc_list}\n")
        fout.write(f"{target_loc_list}\n")
        fout.write(f"{target_obj_loc_list}\n")

    return LMP_env, lmp_high_level

"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Main function

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""

def robotouille_exec_main(model_name_list, demo_version, render):
    """
    Main function to execute code in the robotouille domain

    For example, 
        if model_name_list = ['demo2code'], demo_version = 'latest':
            for each code specified in the demonstrations config file in 'latest_demo-config.txt', 
                it will execute code that are stored in 'outputs/robotouille/code/demo2code/{prompt_version}/' folder
                    (where {prompt_version} is specified by the demo2code_prompt.yaml file in 'data/robotouille/prompt/demo2code/' folder)
                    the code was generated based on demonstrations files in 'data/robotouille/demonstration/demo2code/{demo_version}/' folder

    Parameters:
        model_name_list (list): a list that is a subset of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        demo_version (str): this correspond to the version of demonstrations that will get used
        render (bool): whether to render the env
    """
    for model_name in model_name_list:
        execute_code_based_on_demo_config(model_name, 
                                            demo_version, 
                                            render)

if __name__ == "__main__":
    """
    Step 2: execute the code
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--demo_version", type=str, default = "latest"
    )
    parser.add_argument(
        '--model_names', 
        choices=['spec2code', 'lang2code', 'demonolang2code', 'demo2code'], 
        nargs='+', 
        default=['spec2code', 'lang2code', 'demonolang2code', 'demo2code'],
        help="names of the lmps to execute"
    ) # example --model_names spec2code lang2code demonolang2code demo2code
    parser.add_argument(
        '--render',
        action='store_true',
        help="whether to render the environment"
    )
    args = parser.parse_args()

    robotouille_exec_main(args.model_names, args.demo_version, args.render)
import numpy as np
from matplotlib import pyplot as plt
import os
import re
import copy
import shapely
from shapely.geometry import *
from shapely.affinity import *

import argparse

import json
import yaml

from scripts.overall_helpers.model_config_all import model_cfg_all
from scripts.overall_helpers.lmp import LMP
from scripts.overall_helpers.utils import safe_mkdir, convert_str_to_list, ExecError

from scripts.tabletop_helpers.tabletop_env import PickPlaceEnv
from scripts.tabletop_helpers.helper_lmp import helper_lmp_cfg
from scripts.tabletop_helpers.tabletop_API import LMP_wrapper
from scripts.tabletop_helpers.tabletop_constants import *

from moviepy.editor import ImageSequenceClip


"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Helpfer functions

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""

def execute_code_for_one_demo(model_name, base_name, prompt_version, demo_version, 
                              init_obj_pos_list, active_obj_list = [], 
                              save_obj_pos_filename="", save_state_base_name = "",
                              rand_obj_list_order = False,
                              render=True, save_video=False):
    """
    Execute the code generated for one set of demos. 

    Parameters:
        model_name (str) - one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        base_name (str) - in the format of {model_name}_{example_name}_{description_opt}_{id_num}
            this specifies the corresponding code to execute (and the set of demonstrations that the code is generated from)
        prompt_version (str) - the version of {model_name}'s prompt
            this specifies where the generated code is
        demo_version (str): this correspond to the version of demonstrations that will get used
        init_obj_pos_list (list) - empty list if the object positions initialized by this environment should be saved
                                    else, use this list to intialize the objects in the environment
        active_obj_list (list) - list of objects that are relevant to the task
        save_obj_pos_filename (str) - if non-empty, this is where the object positions initialized by this environment should be saved
        save_state_base_name (str) - filename of where the state trajectory should be saved
        rand_obj_list_order (bool) - True if the env should randomize the order of the object list

        Rendering parameters:
            render (bool) - True if the env should take snapshot of the env when the policy is executing in order to render a video
            save_video (bool) - True if we should save the video based on the task name instead of saving it as preview.webm
    """
    print(f"Executing code generated for demo={base_name}_demo.txt")

    _, example_name, description_opt, _ = base_name.split("_")

    with open(f"./data/tabletop/demonstration/{model_name}/{demo_version}/{base_name}_demo.txt", "r") as f_in:
        raw_demonstrations = f_in.read().strip()

    obj_list_str, _, _ = raw_demonstrations.partition("\n")
    # because the string starts with 'objects=', need to get rid of that
    obj_list_str = obj_list_str[8:]
    obj_list = convert_str_to_list(obj_list_str)
    
    if save_state_base_name == "":
        state_save_path = f"./outputs/tabletop/state/{model_name}/{prompt_version}/{base_name}_state.txt"
    else:
        state_save_path = f"./outputs/tabletop//state/{model_name}/{prompt_version}/{save_state_base_name}_state.txt"

    exec_status = -1

    obj_placement_dict = {}
    if example_name == "place-on-hidden" and description_opt != "none-specific":
        # this task requires objects to be stacked on top of each other initially
        # need to use the active object list to construct an object placement dictionary
        target_obj_index = int(description_opt.split("-")[-1][-1]) - 1

        if active_obj_list == []:
            print("stop: active object should not be empty")
            assert False

        target_obj = active_obj_list[target_obj_index]
        obj_placement_dict[target_obj] = active_obj_list[2:]

    on_table_min_dist_btw_objs = MIN_DIST_BTW_OBJS
    # try executing until it doesn't run into any error because it cannot find a good placement location on table
    while exec_status == -1:
        env, lmp_tabletop_ui, obj_pos_list = init_env_lmp(obj_list, model_name, 
                                            state_save_path,
                                            on_table_min_dist_btw_objs,
                                            init_obj_pos_list,
                                            obj_placement_dict,
                                            rand_obj_list_order=rand_obj_list_order,
                                            render=render)
        
        # save the object position list if needed
        if init_obj_pos_list == []:
            obj_pos_arr = np.array(obj_pos_list).reshape((len(obj_pos_list), 3))

            with open(f"{save_obj_pos_filename}/{base_name}_obj-pos.npy", "wb") as fout:
                np.save(fout, obj_pos_arr, allow_pickle=False)

        env.cache_video = []

        # execute the code
        exec_status = lmp_tabletop_ui(raw_demonstrations, context='', 
                                      load_code_path = f"./outputs/tabletop/code/{model_name}/{prompt_version}/{base_name}_code.txt"  # where to load the generated code
                                      )

        # assume the env raised an execution error because it cannot find a valid placement for all object, 
        #   we retry while decreasing the minimum distance between object
        on_table_min_dist_btw_objs -= MIN_DIST_BTW_OBJS_DECREMENT_AMT
        on_table_min_dist_btw_objs = max(SMALLEST_MIN_DIST_BTW_OBJS, on_table_min_dist_btw_objs)

    env.log_init_predicates()

    if env.cache_video:
        rendered_clip = ImageSequenceClip(env.cache_video, fps=35 if env.high_frame_rate else 25)
        if save_video:
            rendered_clip.write_videofile(f"./outputs/tabletop/videos/{model_name}/{base_name}.webm")
        else:
            rendered_clip.write_videofile(f"./outputs/tabletop/videos/preview.webm")

    return exec_status


def execute_code_based_on_demo_config(model_name, demo_version, obj_lists_used_path, 
                                      initialize_obj_pos=False,
                                      render=False, save_video=False):
    """
    Execute all the code specified by the demo config file stored at 'data/tabletop/demonstration_config/{demo_version}_demo-config.txt'
        the code are loaded based on the prompt_version in the '/data/tabletop/prompt/{model_name}/{model_name}_prompt.yaml' file
            code is stored in 
    
    Parameters:
        model_name (str) - one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        demo_version (str): this correspond to the version of demonstrations that will get used
        obj_lists_used_path (str) - path to the file that contains all the objects used for each task
        init_obj_pos_path (str) - path to the folder that contains all the object positions

        Rendering parameters:
            render (bool) - True if the env should take snapshot of the env when the policy is executing in order to render a video
            save_video (bool) - True if we should save the video based on the task name instead of saving it as preview.webm
    """
    print("Reading from prompt YAML file...")
    with open(f"./data/tabletop/prompt/{model_name}/{model_name}_prompt.yaml", "r") as f:
        prompt_dict = yaml.safe_load(f)

    prompt_version = prompt_dict["prompt_version"].strip()

    # make the directory to store the states
    safe_mkdir(f"./outputs/tabletop/state/{model_name}/{prompt_version}")

    demo_config_filename = f"{demo_version}_demo-config"

    with open(f"./data/tabletop/demonstration_config/{demo_config_filename}.txt", "r") as fin:
        demo_config_list = fin.read().splitlines()

    with open(obj_lists_used_path, "r") as fin:
        obj_lists_to_use = fin.read().splitlines()

    if initialize_obj_pos:
        # make a new folder to hold the object positions
        save_obj_pos_filename = f"./data/tabletop/demonstration_config/obj_pos/{prompt_version}"
        safe_mkdir(save_obj_pos_filename)
    else:
        # no need to save the object positions
        save_obj_pos_filename = ""

    # where to store the execution status (whether the code successfully executes without any runtime error)
    exec_status_json_fp = f"./outputs/tabletop/eval_result/{model_name}/{model_name}_{prompt_version}_exec-status.json"

    if not os.path.isfile(exec_status_json_fp):
        # initialize the exec_status_dict
        exec_status_dict = {}
    else:
        with open(exec_status_json_fp, "r") as fin:
            exec_status_dict = json.load(fin)

    for i in range(len(demo_config_list)):
        example_name, description_opt, id_num = demo_config_list[i].split(',')
        
        base_name = f"{model_name}_{example_name}_{description_opt}_{id_num}"

        if not os.path.isfile(f"./outputs/tabletop/state/{model_name}/{prompt_version}/{base_name}_state.txt"):
            active_obj_list = convert_str_to_list(obj_lists_to_use[2 * i + 1])

            if not initialize_obj_pos:
                with open(f"./data/tabletop/demonstration_config/obj_pos/{demo_version}/{example_name}_{description_opt}_{id_num}_obj-pos.npy", "rb") as fin:
                    init_obj_pos = np.load(fin, allow_pickle=False)
            else:
                init_obj_pos = []

            exec_result = execute_code_for_one_demo(model_name, base_name, prompt_version, demo_version,
                                                            init_obj_pos, 
                                                            active_obj_list,
                                                            save_obj_pos_filename,
                                                            rand_obj_list_order = example_name == "stack-all-objects",
                                                            render=render, save_video=save_video)

            if example_name not in exec_status_dict:
                exec_status_dict[example_name] = {}

            if description_opt not in exec_status_dict[example_name]:
                exec_status_dict[example_name][description_opt] = {}

            exec_status_dict[example_name][description_opt][id_num] = exec_result
            
            with open(exec_status_json_fp, "w") as fout:
                fout.write(json.dumps(exec_status_dict, indent=4))


def init_env_lmp(obj_list, model_name, state_save_path, 
                 on_table_min_dist_btw_objs, 
                 init_obj_pos_list=[], 
                 obj_placement_dict={}, 
                 rand_obj_list_order=False, 
                 render=True, high_resolution=False, high_frame_rate=False):
    """
    Initialize the table top manipulation environment

    Parameters:
        obj_list (list) - list of objects to include in this environment
        model_name (str) - one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        state_save_path (str) - path to save the state trajectories generated when the code is executing
        on_table_min_dist_btw_objs (float) - the minimum distance between object on table
        init_obj_pos_list (list) - if the env has been initialized before, the env will place the object based on this object
        obj_placement_dict (dict) - if the task requires object to be stacked on top of each other, this specify how the objects should be stacked
        rand_obj_list_order (bool) - True if the env should randomize the order of the object list
        Rendering parameters:
            render (bool) - True if the env should take snapshot of the env when the policy is executing in order to render a video
            high_resolution (bool) - True if the snapshot should have high resolution
            high_frame_rate (bool) - True if more snapshots should be taken to have high frame rate videos
    """
    env = PickPlaceEnv(state_save_path, on_table_min_dist_btw_objs, 
                       render=render, high_res=high_resolution, high_frame_rate=high_frame_rate)
    
    min_dist_btw_objs = MIN_DIST_BTW_OBJS
    while True:
        try:
            _, obj_pos_list = env.reset(obj_list, init_obj_pos_list, obj_placement_dict, min_dist_btw_objs = min_dist_btw_objs)
            break
        except ExecError:
            # the env is not able to reset because it cannot find a valid placement for all object, we retry while decreasing the minimum distance between object
            min_dist_btw_objs -= MIN_DIST_BTW_OBJS_DECREMENT_AMT
            min_dist_btw_objs = max(SMALLEST_MIN_DIST_BTW_OBJS, min_dist_btw_objs)
            print(f"retry initializing the environment with min_dist={min_dist_btw_objs}...")

    # load the base prompt based on the the prompt file specified in the configuration
    model_cfg = model_cfg_all[model_name]

    return env, setup_tabletop_LMP(env, helper_lmp_cfg, model_name, model_cfg, rand_obj_list_order, obj_list), obj_pos_list


def setup_tabletop_LMP(env, cfg_tabletop, high_level_model_name, high_level_lmp_cfg, rand_obj_list_order, object_list):
    """
    Adapted from CodeAsPolicies code base: https://github.com/google-research/google-research/tree/master/code_as_policies
    
    Set up all the LMPs (modules to query LLMs and generate code/response)

    Parameters:
        env (PickPlaceEnv): the pick and place environment
        cfg_tabletop (dictionary): store the configuration for helper LMP in this environment 
            (parse_obj_name and parse_position)
        high_level_model_name (str): one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        high_level_lmp_cfg (dictionary): configuration for the {high_level_model_name}
        rand_obj_list_order (bool) - True if the env should randomize the order of the object list
        obj_list (list) - list of objects in this environment
    """
    # LMP env wrapper
    cfg_tabletop = copy.deepcopy(cfg_tabletop)
    cfg_tabletop['env'] = dict()
    cfg_tabletop['env']['init_objs'] = list(env.obj_name_to_id.keys())
    cfg_tabletop['env']['coords'] = lmp_tabletop_coords
    LMP_env = LMP_wrapper(env, cfg_tabletop, randomize=rand_obj_list_order)

    # creating APIs that the LMPs can interact with
    fixed_vars = {
        'np': np
    }
    fixed_vars.update({
        name: eval(name)
        for name in shapely.geometry.__all__ + shapely.affinity.__all__
    })
    variable_vars = {
        k: getattr(LMP_env, k)
        for k in [
            'get_bbox', 'get_obj_pos', 'get_obj_xy_pos', 'get_color', 'is_obj_visible', 'denormalize_xy',
            'put_first_on_second', 'get_obj_names',
            'get_corner_name', 'get_edge_name',
            'get_all_obj_names_that_match_type',
            'stack_without_height_limit', 'stack_with_height_limit', 
            'determine_final_stacking_order'
        ]
    }
    variable_vars['ALL_CORNERS_LIST'] = ['top left corner', 'top right corner', 'bottom left corner', 'bottom right corner']
    variable_vars['ALL_EDGES_LIST'] = ['top edge', 'bottom edge', 'left edge', 'right edge']
    variable_vars['ALL_POSITION_RELATION_LIST'] = ['left of', 'right of', 'behind', 'in front of']
    variable_vars['objects'] = copy.deepcopy(object_list)

    # creating other low-level LMPs
    variable_vars.update({
        k: LMP(k, cfg_tabletop['lmps'][k], fixed_vars, variable_vars)
        for k in ['parse_obj_name', 'parse_position']
    })

    # creating the LMP that deals w/ high-level
    lmp_tabletop_ui = LMP(
        high_level_model_name, high_level_lmp_cfg, fixed_vars, variable_vars, return_exec_status=True
    )

    return lmp_tabletop_ui


"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Main function

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""

def tabletop_exec_main(model_name_list, demo_version, initialize_obj_pos=False, render=False):
    """
    Main function to execute code in the tabletop domain

    For example, 
        if model_name_list = ['demo2code'], demo_version = 'latest':
            for each code specified in the demonstrations config file in 'latest_demo-config.txt', 
                it will execute code that are stored in 'outputs/tabletop/code/demo2code/{prompt_version}/' folder
                    (where {prompt_version} is specified by the demo2code_prompt.yaml file in 'data/tabletop/prompt/demo2code/' folder)
                    the code was generated based on demonstrations files in 'data/tabletop/demonstration/demo2code/{demo_version}/' folder

    Parameters:
        model_name_list (list): a list that is a subset of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        demo_version (str): this correspond to the version of demonstrations that will get used
            it will use object list based on '{demo_version}_demo-config.txt' file
        initialize_obj_pos (bool): whether to initialize the object's position
        render (bool): whether to render the env and save the rendering in a temporary video
    """
    for model_name in model_name_list:
        execute_code_based_on_demo_config(model_name, demo_version,
                                    obj_lists_used_path=f"./data/tabletop/demonstration_config/{demo_version}_demo-obj-lists-used.txt",
                                    initialize_obj_pos=initialize_obj_pos,
                                    render=render)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute the code in tabletop env")
    parser.add_argument("--demo_version", type=str, default="latest")
    parser.add_argument(
        '--model_names', 
        choices=['spec2code', 'lang2code', 'demonolang2code', 'demo2code'], 
        nargs='+', 
        default=['spec2code', 'lang2code', 'demonolang2code', 'demo2code'],
        help="names of the lmps to execute"
    ) # example --model_names spec2code lang2code demonolang2code demo2code
    parser.add_argument("--initialize_obj_pos", action="store_true", default=False)
    parser.add_argument("--render", action="store_true", default=False)

    args = parser.parse_args()
    
    tabletop_exec_main(args.model_names, args.demo_version, args.initialize_obj_pos, args.render)
import argparse

from scripts.tabletop_helpers.tabletop_constants import *

from scripts.code_generation import generate_code_based_on_demo_config

from scripts.tabletop_main import tabletop_exec_main
from scripts.tabletop_evaluator import tabletop_overall_eval

from scripts.robotouille_main import robotouille_exec_main
from scripts.robotouille_evaluator import robotouille_overall_eval

# from scripts.epic_kitchen_evaluator import epickitchen_overall_eval


def run_overall_tabletop_pipeline(model_names, demo_version, render=False):
    # Part 1: generate the code
    for model_name in model_names:
        generate_code_based_on_demo_config(model_name, "tabletop", demo_version)

    # Part 2: execute the code in the env
    tabletop_exec_main(model_names, demo_version, initialize_obj_pos=False, render=render)

    # Part 3: evaluate the performance
    tabletop_overall_eval(demo_config_filename=f"{demo_version}_demo-config", 
                          obj_lists_used_path=f"./data/tabletop/demonstration_config/{demo_version}_demo-obj-lists-used.txt")
    

def run_overall_robotouille_pipeline(model_names, demo_version, render=False):
    # Part 1: generate the code
    for model_name in model_names:
        generate_code_based_on_demo_config(model_name, "robotouille", demo_version)

    # Part 2: execute the code in the env
    robotouille_exec_main(model_names, demo_version, render)

    # Part 3: evaluate the performance
    robotouille_overall_eval(model_names, demo_version)


# def run_overall_epickitchen_pipeline(model_names, demo_version, render=False):
#     # Part 1: generate the code
#     for model_name in model_names:
#         generate_code_based_on_demo_config(model_name, "epickitchen", demo_version)

#     # Part 2: skipped because we do not have a simulator

#     # Part 3: evaluate the performance
#     epickitchen_overall_eval(demo_config_filename=f"{demo_version}_demo-config")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "domain_name", type=str, choices={'TABLETOP', 'ROBOTOUILLE', "EPICKITCHEN"},
        help="domain to generate the code for"
    )
    parser.add_argument(
        '--model_names', 
        choices=['spec2code', 'lang2code', 'demonolang2code', 'demo2code'], 
        nargs='+', 
        default=['spec2code', 'lang2code', 'demonolang2code', 'demo2code'],
        help="names of the lmps to execute"
    ) # example --model_names spec2code lang2code demonolang2code demo2code
    parser.add_argument(
        "--demo_version", type=str, default = "latest"
    )
    parser.add_argument(
        '--render',
        action='store_true',
        help="whether to render the environment",
        default=False
    )
    
    args = parser.parse_args()

    if args.domain_name == "TABLETOP":
        run_overall_tabletop_pipeline(args.model_names, args.demo_version, args.render)
    elif args.domain_name == "ROBOTOUILLE":
        run_overall_robotouille_pipeline(args.model_names, args.demo_version, args.render)
    # elif args.domain_name == "EPICKITCHEN":
    #     run_overall_epickitchen_pipeline(args.model_names, args.demo_version, args.render)
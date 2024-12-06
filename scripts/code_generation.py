import os
import openai

openai.api_key = os.environ["OPENAI_API_KEY"]

from scripts.overall_helpers.code_gen_helper import code_generator

from scripts.overall_helpers.utils import safe_mkdir

import argparse
import shutil
import yaml

"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Helpfer functions

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""

def generate_code_for_one_demo(model_name, domain_name, demo_version, base_name, prompt_version, prompt_dict):
    """
    For one task (one set of demonstrations specified by base_name), generate code using one model

    Parameters:
        model_name (str): one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        domain_name (str): one of ['tabletop', 'robotouille', "epickitchen"]
        demo_version (str): this correspond to the version of demonstrations that will get used
            it will generate code based on '{demo_version}_demo-config.txt' file, using demonstrations in the 'demo_version"'folder 
        base_name (str): specify the set of demonstration by '{model_name}_{example_name}_{description_opt}_{id_num}'
            this is also the base name for the code and the chain-of-thought
        prompt_version (str): the version of {model_name}'s prompt
            this specifies where the generated code and chain-of-thought will be stored
        prompt_dict (dictionary): contain the prompt for {model_name}
    """
    print(f"Generating code for domain={domain_name} with model={model_name} for demo={base_name}_demo.txt")

    with open(f"./data/{domain_name}/demonstration/{model_name}/{demo_version}/{base_name}_demo.txt", "r") as f_in:
        demonstrations = f_in.read().strip()

    code_save_path = f"./outputs/{domain_name}/code/{model_name}/{prompt_version}/{base_name}_code.txt"

    if "demo" in model_name:
        cot_save_path = f"./outputs/{domain_name}/cot/{model_name}/{prompt_version}/{base_name}_cot.txt"
    else:
        cot_save_path = ""

    # go through the model's pipeline to generate code
    code_generator(model_name, prompt_dict, demonstrations, code_save_path, cot_save_path)

    
def generate_code_based_on_demo_config(model_name, domain_name, demo_version):
    """
    For one model, generate code for a domain based on the '{demo_version}_demo-config.txt' in 'data/{domain_name}/demonstration_config/' folder

    Parameters:
        model_name_list (list): a list that is a subset of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        domain_name (str): one of ['tabletop', 'robotouille', "epickitchen"]
        demo_version (str): this correspond to the version of demonstrations that will get used
            it will generate code based on '{demo_version}_demo-config.txt' file, using demonstrations in the 'demo_version"'folder 
    """
    with open(f"./data/{domain_name}/demonstration_config/{demo_version}_demo-config.txt", "r") as fin:
        demo_config_list = fin.read().splitlines()

    print("Reading from prompt YAML file...")
    prompt_yaml_fp = f"./data/{domain_name}/prompt/{model_name}/{model_name}_prompt.yaml"
    with open(prompt_yaml_fp, "r") as f:
        prompt_dict = yaml.safe_load(f)

    print("Save the latest version of this prompt YAML fiel...")
    shutil.copyfile(prompt_yaml_fp, f"./data/{domain_name}/prompt/{model_name}/prompt_archive/{model_name}_v={prompt_dict['prompt_version']}_prompt.yaml")

    prompt_version = prompt_dict["prompt_version"].strip()

    # make the directory to storestore all the generated code
    safe_mkdir(f"./outputs/{domain_name}/code/{model_name}/{prompt_version}")
    if "demo" in model_name:
        # save the chain-of-thought for demo2code and demonolang2code
        safe_mkdir(f"./outputs/{domain_name}/cot/{model_name}/{prompt_version}")

    for i in range(len(demo_config_list)):
        example_name, description_opt, id_num = demo_config_list[i].split(',')

        base_name = f"{model_name}_{example_name}_{description_opt}_{id_num}"

        if not os.path.isfile(f"./outputs/{domain_name}/code/{model_name}/{prompt_version}/{base_name}_code.txt"):
            generate_code_for_one_demo(model_name, domain_name, demo_version, base_name, prompt_version, prompt_dict)



"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Main function

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""

def code_gen_main(model_name_list, domain_name, demo_version):
    """
    Main function to generate code. 

    For example, 
        if model_name_list = ['demo2code'], domain_name = 'robotouille', demo_version = 'latest':
            it will generate code for the 'robotouille' domain 
                based on demonstrations config file in 'latest_demo-config.txt', 
                and use demonstration files in 'data/robotouille/demonstration/demo2code/{demo_version}/' folder


    Parameters:
        model_name_list (list): a list that is a subset of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        domain_name (str): one of ['tabletop', 'robotouille', "epickitchen"]
        demo_version (str): this correspond to the version of demonstrations that will get used
            it will generate code based on '{demo_version}_demo-config.txt' file, using demonstrations in the 'demo_version"'folder 
    """
    for model_name in model_name_list:
        generate_code_based_on_demo_config(model_name, 
                                        domain_name,
                                        demo_version)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code generator using gpt-3.5")
    parser.add_argument(
        "domain_name", type=str, choices={'TABLETOP', 'ROBOTOUILLE', "EPICKITCHEN"},
        help="domain to generate the code for"
    )
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

    args = parser.parse_args()

    domain_name = args.domain_name.lower()

    code_gen_main(args.model_names, domain_name, args.demo_version)
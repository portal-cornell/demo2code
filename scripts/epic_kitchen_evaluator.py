from overall_helper.utils import *
from overall_helper.eval_helper import compute_bleu_score_for_code

from overall_helper.constants import EPICKITCHEN

import argparse
import yaml
import json

def bleu_eval_for_one_model(lmp_name, prompt_version, query_config_filename):
    """
    Given a query config, run token-wise comparison between the oracle code (spec2code) and the current model's code
    
    Return:
        a dictionary where the key is "{example_name},{description_opt}" and the value is the token comparison score for 
        each example that fits in the category
    """
    with open(f".{EPICKITCHEN}/query/configs/{query_config_filename}.txt", "r") as fin:
        query_config_list = fin.read().splitlines()

    result_dict = {}

    for i in range(len(query_config_list)):
        example_name, description_opt, id_num = query_config_list[i].split(',')

        with open(f".{EPICKITCHEN}/code/ref_code/ref_{example_name}_{description_opt}_{id_num}_code.txt", "r") as fin:
            ref_code = fin.read()

        with open(f".{EPICKITCHEN}/code/{lmp_name}/{prompt_version}/{lmp_name}_{example_name}_{description_opt}_{id_num}_code.txt", "r") as fin:
            lmp_code = fin.read()

        result = compute_bleu_score_for_code(ref_code, lmp_code)

        if description_opt == "none-specific":
            description_opt = "none"

        key = f"{example_name},{description_opt}"
        
        if key not in result_dict:
            result_dict[key] = []

        result_dict[key].append(result)

    return result_dict

def epickitchen_overall_eval(query_config_filename):
    with open(f".{EPICKITCHEN}/prompts/demo2code/demo2code_latest_prompt.yaml", "r") as f:
        prompt_dict = yaml.safe_load(f)

    prompt_version = prompt_dict["prompt_version"].strip()

    overall_result_dict = {}

    for lmp_name in ["spec2code", "lang2code", "demonolang2code", "demo2code"]:
        overall_result_dict[lmp_name] = bleu_eval_for_one_model(lmp_name, prompt_version, query_config_filename)
    
    with open(f".{EPICKITCHEN}/results/{prompt_version}_overall-results.json", "w") as fout:
        fout.write(json.dumps(overall_result_dict, indent=4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the generated code for EPIC-KITCHEN dataset")
    parser.add_argument("--query_version", type=str, default="latest")
    args = parser.parse_args()

    epickitchen_overall_eval(f"{args.query_version}_query-config")
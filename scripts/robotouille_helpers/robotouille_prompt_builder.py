from robotouille_helpers.robotouille_template import robotouille_prompt_template, predicates_to_lang
from overall_helper.constants import ROBOTOUILLE
import re

def clarify_name(name, change_id):
    if "robot" in name:
        return name
    
    id_num_offset = 2 if change_id else 0

    re_compile = re.compile("([a-zA-Z]*)([0-9]*)")
    
    obj_type = re_compile.search(name).group(1)
    id_num = int(re_compile.search(name).group(2))
    # offset the id
    id_num = str(id_num + id_num_offset)

    if "topbun" in obj_type:
        return "top_bun" + id_num
    elif "bottombun" in obj_type:
        return "bottom_bun" + id_num
    elif "board" in obj_type:
        return "cutting_board" + id_num

    return obj_type + id_num

def translate_predicate_to_language(predicate_str, change_id):
    predicate_name, _, rest = predicate_str.partition("(")
    
    if predicate_name == "":
        return ""

    objs, _, true = rest.partition(")")
    true = true[1:]

    objs_list = objs.split(",")
    objs_list = [obj.split(":")[0] for obj in objs_list]

    language_repr = predicates_to_lang[predicate_name]

    for i in range(len(objs_list)):
        obj_name = clarify_name(objs_list[i], change_id)
        keyword_to_replace = f"<{i + 1}>"

        # replacing the placeholder with the correct object name
        language_repr = language_repr.replace(keyword_to_replace, obj_name)

    if true == '0':
        boolean_repr = "not "
    else:
        boolean_repr = ""
    
    language_repr = language_repr.replace("<true>", boolean_repr)

    return language_repr

def format_one_rollout_state_trans(state_trans_str, change_id=False):
    init_state_formatted = "Initial State (State 1):\n"

    states_str_b4_init, _, init_state_str  = state_trans_str.partition("<init-state>")

    init_state_list = [x for x in init_state_str.split("\n") if x != ""]
    # print(init_state_list)

    for predicate in init_state_list:
        init_state_formatted += f"{translate_predicate_to_language(predicate, change_id)}\n"

    # print()
    # print(init_state_formatted)

    states_str_b4_init_list = states_str_b4_init.split("<state-")[1:]

    states_formatted = ""

    for states_str in states_str_b4_init_list:
        state_num, _, predicates_str = states_str.partition(">\n")
        states_formatted += f"State {state_num}:\n"

        # get rid of the trailing new lines
        predicates_str, _, _ = predicates_str.partition("\n\n")

        for predicate in predicates_str.split("\n"):
            states_formatted += f"{translate_predicate_to_language(predicate, change_id)}\n"

        states_formatted += "\n"
            
    # print(states_formatted)
    
    return init_state_formatted, states_formatted


def merge_init_state_strs(init_state_str_list):
    """
    Assume the len > 1
    """
    to_include_list = []

    for i in range(len(init_state_str_list)):
        # prev_init_state_list = init_state_str_list[i-1].split("\n")[1:-1]
        curr_init_state_list = init_state_str_list[i].split("\n")[1:-1]

        for state_str in curr_init_state_list:
            if state_str not in to_include_list:
                to_include_list.append(state_str)

    overall_init_state_str = "Initial State (State 1):\n"
    overall_init_state_str += "\n".join(to_include_list)
    overall_init_state_str += "\n"

    return overall_init_state_str

def format_overall_state_trans(example_config, folder_base_name, is_prompt=False):
    """
    if none is in the description_opt, we need to load both scenario
    otherwise, we only load one
    if we don't have valid state transitions, we discard generating the code for this example by 
    """
    example_name, description_opt = example_config

    base_name_no_id = f"cap-full_{example_name}_{description_opt}"

    prompt_path = "-prompt" if is_prompt else ""
    with open(f".{ROBOTOUILLE}/state/cap-full/{folder_base_name}{prompt_path}/{base_name_no_id}_100_state.txt", "r") as fin:
        state_trans_s1 = fin.read()

    # invalid state, no need to generate for the rest
    if state_trans_s1 == "<init-state>\n":
        print(f"{base_name_no_id}-100")
        input("stop")
        return ""
    
    init_state_str, states_s1_str = format_one_rollout_state_trans(state_trans_s1)

    with open(f".{ROBOTOUILLE}/state/cap-full/{folder_base_name}{prompt_path}/{base_name_no_id}_101_state.txt", "r") as fin:
        state_trans_s2 = fin.read()

    init_state_str_s2, states_s2_str = format_one_rollout_state_trans(state_trans_s2, change_id=True)

    overall_states_str = f"[Scenario 1]\n{robotouille_prompt_template[example_name]['command']}\n\n{states_s1_str[:-1]}\n[Scenario 2]\n{robotouille_prompt_template[example_name]['command']}\n\n{states_s2_str[:-1]}"

    return overall_states_str

if __name__ == "__main__":
    # example_config = ("high-level-assemble-burgers", "parallel")
    # example_config = ("high-level-cook-and-cut", "cut-first")
    # example_config = ("high-level-lettuce-burger", "substitute-onions")
    example_config = ("high-level-two-lettuce-burger", "cut-lettuces")
    print(format_overall_state_trans(example_config=example_config,
                               folder_base_name="05-15",
                               is_prompt=False))
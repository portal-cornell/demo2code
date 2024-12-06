from tabletop_helpers.tabletop_build_template import prompt_template, predicates_to_lang
from scripts.tabletop_helpers.tabletop_constants import *
from scripts.overall_helpers.utils import cprint, convert_str_to_list, safe_mkdir

def translate_predicate_to_language(predicate_str):
    predicate_name, objs, true = predicate_str.split(":")
    objs_list = objs.split(",")

    language_repr = predicates_to_lang[predicate_name]

    for i in range(len(objs_list)):
        obj_name = objs_list[i]
        keyword_to_replace = f"<obj_{i + 1}>"

        # replacing the placeholder with the correct object name
        language_repr = language_repr.replace(keyword_to_replace, obj_name)

    if true == '0':
        boolean_repr = "not "
    else:
        boolean_repr = ""
    
    language_repr = language_repr.replace("<true>", boolean_repr)

    # print(language_repr)

    return language_repr

def format_one_rollout_state_trans(state_trans_str):
    init_state_formatted = "Initial State (State 1):\n"

    states_str_b4_init, _, init_state_str  = state_trans_str.partition("<init-state>")

    init_state_list = [x for x in init_state_str.split("\n") if x != ""]
    # print(init_state_list)

    for predicate in init_state_list:
        init_state_formatted += f"{translate_predicate_to_language(predicate)}\n"

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
            states_formatted += f"{translate_predicate_to_language(predicate)}\n"

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
    example_name_full, description_opt, code_opt, id_num = example_config

    if "stack-all-type" in example_name_full:
        example_name, example_obj_type = example_name_full.split("=")

        if example_obj_type != "block" and example_obj_type != "cylinder":
            print("invalid object type")
            print(example_obj_type)
            input("check error")
    else:
        example_name = example_name_full
        example_obj_type = ""

    if code_opt == "none":
        og_description_opt = "none-specific"
    else:
        og_description_opt = code_opt

    base_name = f"cap-full_{example_name_full}_{og_description_opt}_{id_num}"

    prompt_path = "-prompt" if is_prompt else ""
    with open(f"./state/cap-full/{folder_base_name}{prompt_path}/{base_name}_state.txt", "r") as fin:
        state_trans_s1 = fin.read()

    # invalid state, no need to generate for the rest
    if state_trans_s1 == "<init-state>\n":
        print(base_name)
        input("stop")
        return ""
    
    init_state_str, states_s1_str = format_one_rollout_state_trans(state_trans_s1)

    general_case = code_opt == "none" and example_name != 'place-on-hidden' and 'stack-all-type' not in example_name and example_name != 'stack-all-objects'
    stack_all_type_ordered = example_name == "stack-all-type-order" and code_opt != "fully-ordered" and code_opt != "none" and code_opt != "none-specific"

    if stack_all_type_ordered or general_case:
        with open(f"./state/cap-full/{folder_base_name}{prompt_path}/{base_name}_s2_state.txt", "r") as fin:
            state_trans_s2 = fin.read()

        init_state_str_s2, states_s2_str = format_one_rollout_state_trans(state_trans_s2)

        overall_init_state_str = merge_init_state_strs([init_state_str, init_state_str_s2])

        overall_states_str = f"{overall_init_state_str}\n[Scenario 1]\n{states_s1_str[:-1]}\n[Scenario 2]\n{states_s2_str[:-1]}"
    else:
        overall_states_str = f"{init_state_str}\n[Scenario 1]\n{states_s1_str[:-1]}"

    return overall_states_str
    

def build_one_example_prompt(llm_name, folder_base_name, example_config, obj_list_str, active_obj_list_str, with_say_setting="", include_code=True):
    """
    randomly initialize the objects in the world environment
        randomly determine 1-k number of a type of obj
    randomly sample the necessary amount of objects for this example (these objs need to be unique)
    assembly the prompt in this order:
        - objects in the scene
        - instruction
        - code
    """
    example_name_full, description_opt, code_opt, id_num = example_config

    if "stack-all-type" in example_name_full:
        example_name, example_obj_type = example_name_full.split("=")

        if example_obj_type != "block" and example_obj_type != "cylinder":
            print("invalid object type")
            print(example_obj_type)
            input("check error")
    else:
        example_name = example_name_full
        example_obj_type = ""

    # initialize the objects in the environment
    if obj_list_str == "":
        min_blocks = 1
        min_cylinders = 1
        max_blocks = MAX_NUM_BLOCKS + 1
        max_cylinders = MAX_NUM_CYLINDERS + 1

        if example_name == "place-on-hidden":
            # because num_objs don't represent the number of active objects for place-on-hidden
            #   we have to figure it out from the description_opt
            if "none" not in description_opt:
                min_total_objs = int(description_opt[0]) + 2
            else:
                min_total_objs = 2

            num_active_objs = min_total_objs

            if min_total_objs >= 5:
                # generate slightly more objects when there must be at least 5 objects
                max_blocks += 1
                max_cylinders += 1
        elif example_name == "stack-all-objects":
            min_total_objs = 6 # at least one stack of 4 and one stack of 2
            min_blocks = 2
            max_blocks = 5
            min_cylinders = 2
            max_cylinders = 5
        elif example_name == "stack-all-type-order":
            min_total_objs = 4 # at least 3 of objects of interest, and at least 1 of the other type

            if example_obj_type == "block":
                min_blocks = 4
                max_blocks = 5
                min_cylinders = 1
                max_cylinders = 4
            else:
                min_cylinders = 4
                max_cylinders = 5
                min_blocks = 1
                max_blocks = 4
        elif example_name == "stack-all-type":
            if "none" not in description_opt:
                # we want to generate at least 1 more object than the max height of a stack
                min_total_objs = int(description_opt[-1])
            else:
                min_total_objs = 2

            if example_obj_type == "block":
                if "none" not in description_opt:
                    min_blocks = min_total_objs + 1
                    max_blocks = int(2 * min_total_objs) + 1 if min_total_objs < 4 else 8
                else:
                    min_blocks = min_total_objs
                    max_blocks = 4 + 1

                max_cylinders = 3
                # TODO: do we want to decrease the number of cylinders? maybe?
            elif example_obj_type == "cylinder":
                if "none" not in description_opt:
                    min_cylinders = min_total_objs + 1
                    max_cylinders = int(2 * min_total_objs) + 1 if min_total_objs < 4 else 8
                else:
                    min_cylinders = min_total_objs
                    max_cylinders = 4 + 1

                max_blocks = 3

            min_total_objs = min_blocks + min_cylinders

            # TODO: need to figure out the maximum block
            # print(min_total_objs)
        else:
            min_total_objs = 2
            num_active_objs = prompt_template[example_name]['num_objs']

        num_blocks = 0
        num_cylinders = 0
        while num_blocks + num_cylinders < min_total_objs:
            num_blocks = np.random.randint(min_blocks, max_blocks)
            num_cylinders = np.random.randint(min_cylinders, max_cylinders)

        # if "stack-all-objects" in example_name:
        #     print(example_config)
        #     print(f"b: {num_blocks}, {min_blocks}, {max_blocks}")
        #     print(f"c: {num_cylinders}, {min_cylinders}, {max_cylinders}")
        #     print(num_blocks + num_cylinders)
        #     input("sotp")

        block_list = np.random.choice(ALL_BLOCKS, size=num_blocks, replace=False).tolist()
        cylinder_list = np.random.choice(ALL_CYLINDERS, size=num_cylinders, replace=False).tolist()
        obj_list = block_list + cylinder_list

        # sample the active objects (objects that are involved with the action)
        if "stack-all-type" in example_name:
            if "stack-all-type-order" in example_name:
                np.random.shuffle(block_list)
                np.random.shuffle(cylinder_list)

            if example_obj_type == "block":
                active_obj_list = block_list
            elif example_obj_type == "cylinder":
                active_obj_list = cylinder_list
        elif example_name == "stack-all-objects":
            active_obj_list = obj_list
        else:
            active_obj_list = np.random.choice(obj_list, size = num_active_objs, replace=False).tolist()
    else:
        obj_list = convert_str_to_list(obj_list_str)
        active_obj_list = convert_str_to_list(active_obj_list_str)

    if description_opt == "default":
        description = prompt_template[example_name]['descriptions']
    else:
        description = prompt_template[example_name]['descriptions'][description_opt]

    if include_code:
        if code_opt == "default":
            code = prompt_template[example_name][f'code{with_say_setting}']
        else:
            if "our" in llm_name and (example_name == "stack-all-type" or example_name == "stack-all-type-order" or example_name == "stack-all-objects"):
                # add Chain-of-thought to the code
                code = prompt_template[example_name][f'code_with-say_cot'][code_opt]
            else:
                code = prompt_template[example_name][f'code{with_say_setting}'][code_opt]

    for i in range(len(active_obj_list)):
        obj_name = active_obj_list[i]
        keyword_to_replace = f"<obj_{i + 1}>"

        # replacing the placeholder with the correct object name
        description = description.replace(keyword_to_replace, obj_name)

        if include_code:
            code = code.replace(keyword_to_replace, obj_name)

    if example_obj_type != "":
        description = description.replace("<type>", example_obj_type)

        if include_code:
            code = code.replace("<type>", example_obj_type)

    if example_name == "stack-all-type-order" and code_opt == "fully-ordered":
        # np.random.shuffle(active_obj_list)
        description = description.replace("<stack_1>", str(active_obj_list))

        if include_code:
            code = code.replace("<stack_1>", str(active_obj_list))

    query_str = f'objects={repr(obj_list)}\n"""\n'

    # need to include state configuration
    if "our" in llm_name:
        state_trans_str = format_overall_state_trans(example_config, folder_base_name, is_prompt=include_code)

        if state_trans_str == "":
            # cannot generate state transition str
            #   discard this example
            print(f"discarding {example_config}")
            input("stop")
            return '', '', ''
        
        if "lang" in llm_name:
            query_str += f'{description}\n\n'

        query_str += f'{state_trans_str}"""'
    else:
        query_str += f'{description}\n"""'

    if include_code:
        if "our" in llm_name and example_name == "stack-all-type":
            if code_opt == "none":
                code = code.replace("<stack_1>", str(active_obj_list))
            elif code_opt == "max-3":
                code = code.replace("<stack_1>", str(active_obj_list[:3]))
                code = code.replace("<stack_2>", str(active_obj_list[3:]))
            else:
                print(description_opt)
                raise NotImplementedError
        
        return query_str, f'{code}', f'{repr(obj_list)}\n{repr(active_obj_list)}'
    else:
        return query_str, '', f'{repr(obj_list)}\n{repr(active_obj_list)}'

def build_prompt(prompt_config_filename, obj_lists_used_path = ""):
    """
    1. Read a prompt configuration file
    2. For each example
        randomly initialize the objects in the world environment
            randomly determine 1-k number of a type of obj
        randomly sample the necessary amount of objects for this example (these objs need to be unique)
        assembly the prompt in this order:
            - objects in the scene
            - instruction
            - code
    3. save the prompt at the target location
    """
    llm_name, prompt_filename = prompt_config_filename.split("_")[:2]

    with open(f"./prompts/{llm_name}/configs/{prompt_config_filename}", "r") as fin:
        prompt_config = fin.read().splitlines()
        # check for the with_say keywords
        with_say = "_with-say" if prompt_config[0] == "with-say" else ""
        prompt_config = prompt_config[1:]
        prompt_config = [example.split(",") for example in prompt_config]

    with open(f"./prompts/headers/prompt-header.txt", "r") as fin:
        prompt = fin.read()

    if llm_name == "cap-full":
        safe_mkdir(f"./query/cap-full/{prompt_filename}-prompt")
        safe_mkdir(f"./code/cap-full/{prompt_filename}-prompt")

        with open(f"./query/configs/{prompt_filename}-prompt_query-config.txt", "w") as fout:
            query_ver_prompt_config = [",".join(x[:2]) + ",0" for x in prompt_config]
            fout.write("\n".join(query_ver_prompt_config))
    
    # add a new line between the header and the examples
    prompt += "\n<header_example_seperator>\n"

    if obj_lists_used_path != "":
        with open(obj_lists_used_path, "r") as fin:
            obj_lists_to_use = fin.read().splitlines()
    else:
        # keep track of the object lists used for each example
        obj_lists_used_in_prompt = ""

    for i in range(len(prompt_config)):
        example_name, description_opt, code_opt = prompt_config[i]

        if obj_lists_used_path != "":
            obj_list_str = obj_lists_to_use[2 * i]
            active_obj_list_str = obj_lists_to_use[2 * i + 1]
        else:
            obj_list_str = ""
            active_obj_list_str = ""

        query, code, obj_list_used = build_one_example_prompt(llm_name, prompt_filename, [example_name, description_opt, code_opt, 0], 
                                                              obj_list_str, active_obj_list_str, with_say_setting=with_say)
        
        """
        We save the query
        """
        if llm_name == "cap-full":
            base_name = f"{llm_name}_{example_name}_{description_opt}_0"

            with open(f"./query/cap-full/{prompt_filename}-prompt/{base_name}_query.txt", "w") as fout:
                fout.write(query)
            with open(f"./code/cap-full/{prompt_filename}-prompt/{base_name}_code.txt", "w") as fout:
                fout.write(code)

        if i != 0:
            prompt += "\n<example_separator>\n"

        prompt += query + "\n<query_code_separator>\n" + code

        if obj_lists_used_path == "":
            obj_lists_used_in_prompt += f"{obj_list_used}\n"

    cprint(prompt)

    with open(f"./prompts/{llm_name}/{llm_name}_{prompt_filename}_prompt.txt", "w") as fout:
        fout.write(prompt)

    if obj_lists_used_path == "":
        with open(f"./prompts/{llm_name}/configs/{llm_name}_{prompt_filename}_obj-lists-used.txt", "w") as fout:
            fout.write(obj_lists_used_in_prompt)


def build_queries(llm_name, query_config_path, obj_lists_used_path = ""):
    query_config_filename = query_config_path.split("_")[0].split("/")[-1]

    # create the folder to store all the queries
    safe_mkdir(f"./query/{llm_name}/{query_config_filename}")

    with open(query_config_path, "r") as fin:
        query_config_list = fin.read().splitlines()
    
    print(query_config_list)

    if obj_lists_used_path != "":
        with open(obj_lists_used_path, "r") as fin:
            obj_lists_to_use = fin.read().splitlines()
    else:
        # keep track of the object lists used for each example
        obj_lists_used_in_prompt = ""

    for i in range(len(query_config_list)):
        example_name, description_opt, id_num = query_config_list[i].split(',')
        description_opt_og = description_opt

        # load the correct object if there is any
        if obj_lists_used_path != "":
            obj_list_str = obj_lists_to_use[2 * i]
            active_obj_list_str = obj_lists_to_use[2 * i + 1]
        else:
            obj_list_str = ""
            active_obj_list_str = ""

        # models beside cap-full should only get vague language description
        if llm_name != "cap-full":
            if description_opt != "default":
                description_opt = "none"

        query, _, obj_list_used = build_one_example_prompt(llm_name, query_config_filename, [example_name, description_opt, description_opt_og, id_num], 
                                                           obj_list_str, active_obj_list_str, include_code=False)

        if obj_lists_used_path == "":
            obj_lists_used_in_prompt += f"{obj_list_used}\n"

        with open(f"./query/{llm_name}/{query_config_filename}/{llm_name}_{example_name}_{description_opt_og}_{id_num}_query.txt", "w") as fout:
            fout.write(query)

    if obj_lists_used_path == "":
        with open(f"./query/configs/{query_config_filename}_query-obj-lists-used.txt", "w") as fout:
            fout.write(obj_lists_used_in_prompt)    


def query_writer(base_query_filename, num_repeats, new_query_filename):
    with open(f"./query/configs/{base_query_filename}", "r") as fin:
        query_config_list = fin.read().splitlines()

    new_query_config_list = []
    for query_config in query_config_list:
        for i in range(num_repeats):
            new_query_config_list.append(f"{query_config},{i}")

    with open(f"./query/configs/{new_query_filename}", "w") as fout:
        fout.write("\n".join(new_query_config_list))

if __name__ == "__main__":
    base_name = '04-08'

    # build_prompt(f"cap-full_{base_name}_config.txt")

    # build_prompt(f"cap-vague_{base_name}_config.txt", f"./prompts/cap-full/configs/cap-full_{base_name}_obj-lists-used.txt")

    # build_prompt(f"our-state_{base_name}_config.txt", f"./prompts/cap-full/configs/cap-full_{base_name}_obj-lists-used.txt")

    # build_prompt(f"our-state-lang_{base_name}_config.txt", f"./prompts/cap-full/configs/cap-full_{base_name}_obj-lists-used.txt")

    # build_queries(llm_name = "cap-full",
    #                 query_config_path=f"./query/configs/{base_name}_query-config.txt",
    #                 obj_lists_used_path="")
    
    # build_queries(llm_name = "cap-vague",
    #                 query_config_path=f"./query/configs/{base_name}_query-config.txt",
    #                 obj_lists_used_path=f"./query/configs/{base_name}_query-obj-lists-used.txt")

    # build_queries(llm_name = "our-state",
    #                 query_config_path=f"./query/configs/{base_name}_query-config.txt",
    #                 obj_lists_used_path=f"./query/configs/{base_name}_query-obj-lists-used.txt")
    
    # build_queries(llm_name = "our-state-lang",
    #                 query_config_path=f"./query/configs/{base_name}_query-config.txt",
    #                 obj_lists_used_path=f"./query/configs/{base_name}_query-obj-lists-used.txt")

    # query_writer('test.txt', 10, 'test2.txt')
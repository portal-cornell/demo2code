from scripts.overall_helpers.lmp import call_openai_api
from scripts.overall_helpers.utils import cprint

"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Main function

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""

def code_generator(model_name, prompt_dict, raw_demonstrations, code_save_path="", cot_save_path=""):
    """
    Based on the {model_name}'s pipeline, generate the code using prompt in {prompt_dict} for {raw_demonstrations}

    Parameters:
        model_name (str): one of ['spec2code', 'lang2code', 'demonolang2code', 'demo2code']
        prompt_dict (dictionary): contain the prompt for {model_name}
        raw_demonstrations (str): text representation of the demonstrations
            for 'lang2code', they will be vague language instruction
            for 'spec2code', they will be detailed language instruction on how to do the task (specification)
        code_save_path (str): path to save the generated code
        cot_save_path (str): path to save the generated chain of thought
    """

    """
    [Stage 1: Recursive Summarization] Demonstrations -> Task Specification (for demonolang2code and demo2code)
    """
    if "demo" in model_name:
        summary_prompt = prompt_dict['stage1']['recursive_summarization']
        summary2spec_prompt = prompt_dict['stage1']['summary_2_spec']
        
        if '"""' in raw_demonstrations:
            # extract environment information (e.g. a set of objects defined for the environment)
            env_info, _, rest = raw_demonstrations.partition('"""')
        else:
            env_info = ""
            rest = raw_demonstrations

        clean_raw_demo = rest.replace('"""', "")
        clean_raw_demo = clean_raw_demo.strip("\n")

        """
        Extract all demos from the raw_demonstrations into a list
        """
        demos_list = []
        i = 1
        while f"[Scenario {i}]" in clean_raw_demo:
            before, _, after = clean_raw_demo.partition(f"[Scenario {i+1}]")

            # prepare the rest of the query for the next loop
            if f"[Scenario {i+1}]" in clean_raw_demo:
                clean_raw_demo = f"[Scenario {i+1}]{after}"
            else:
                clean_raw_demo = ""

            before_states, _, states = before.partition("State 2:")
            if i == 1:
                # if it's the first demo, we want to extract the high level goal
                if "demonolang" in model_name:
                    # there is no language goal
                    lang_goal = ""
                else:
                    _, _, lang_goal = before_states.partition(f"[Scenario {i}]\n")
                    lang_goal = lang_goal.strip("\n")


            states = states.strip("\n")

            if lang_goal != "":
                demo = f"[[Input Trajectory:]]\n[Scenario {i}]\n{lang_goal}\n\nState 2:\n{states}"
            else:
                demo = f"[[Input Trajectory:]]\n[Scenario {i}]\nState 2:\n{states}"
            
            demos_list.append(demo)

            i += 1


        """
        Stage 1: Recursive Summarization
        """
        with open(cot_save_path, "w") as fout:
            # initialize the chain-of-thought save file
            fout.write("")

        task_spec = summarize(demos_list, lang_goal, summary_prompt, summary2spec_prompt, cot_save_path)
        
        if env_info:
            task_spec = f'{env_info}\n"""\n{task_spec}\n"""'
        else:
            task_spec = f'"""\n{task_spec}\n"""'
    else:
        # if there is no demo provided, we directly use the language instruction
        task_spec = raw_demonstrations

    """
    [Stage 2: Recursive Expansion] Task Specifcation -> High Level Code
    """
    spec2highlevelcode_prompt = prompt_dict['stage2']['spec_2_highlevelcode']
    spec_to_high_level_code(task_spec, spec2highlevelcode_prompt, code_save_path)


def summarize(demos_list, lang_goal, summarize_prompt, summary2spec_prompt, cot_save_path, sum_steps_left=4):
    """
    For [Stage 1: Recursive Summarization]
    Recursively summarize the demonstrations in <demos_list>

    Parameters:
        demos_list (list): a list of demonstrations that are currently getting summarized
        lang_goal (str): language describing the general goal of the task
        summarize_prompt (dictionary): dictionary containing "main" and "examples" that defines the LLM prompt to 
            summarize an individual demonstration
        summary2spec_prompt (dictionary): dictionary containing "main" and "examples" that defines the LLM prompt to 
            summarize all concatenated demonstrations together
        cot_save_path (str): path to save the generated chain of thought
        sum_steps_left (int): number of steps allowed to recursively summarize each individual demos
    """
    # we force it to summarize all demos together if it runs out of steps
    if is_summarized(demos_list) or sum_steps_left == 0:
        all_demos = combine_all_demos(demos_list, lang_goal)

        specification = call_openai_api(main_prompt=summary2spec_prompt["main"].strip("\n").strip(), 
                                                raw_examples_list=summary2spec_prompt["examples"],
                                                user_query=all_demos.strip("\n").strip(), 
                                                stop_list=["[[end of response]]"],
                                                temperature=0.0,
                                                max_tokens=8000,
                                                gpt_model="gpt-3.5-turbo-16k")
        
        with open(cot_save_path, "a") as fout:
            fout.write("==========================summary -> spec==========================\n")
            fout.write(specification)
            fout.write("\n\n")

        # remove intermediate reasoning and just return the task specification
        clean_specification = clean_up_specification(specification)

        print("==========================summary -> spec==========================")
        print(clean_specification)
            
        return clean_specification
    else:
        summarized_demos_list = []

        for demo in demos_list:
            demo_query = prepare_demo_query(demo)

            summarized_demo = call_openai_api(main_prompt=summarize_prompt["main"].strip("\n").strip(), 
                                                    raw_examples_list=summarize_prompt["examples"],
                                                    user_query=demo_query.strip("\n").strip(), 
                                                    stop_list=["[[end of response]]"],
                                                    temperature=0.0,
                                                    max_tokens=8000,
                                                    gpt_model="gpt-3.5-turbo-16k")
            
            with open(cot_save_path, "a") as fout:
                fout.write("==========================summarizing demo==========================\n")
                fout.write(summarized_demo)
                fout.write("\n\n")
            
            print("==========================summarizing demo==========================")
            print(summarized_demo)

            summarized_demos_list.append(summarized_demo)
        
        # decrease the number of steps we have
        return summarize(summarized_demos_list, lang_goal, 
                         summarize_prompt, summary2spec_prompt, 
                         cot_save_path, 
                         sum_steps_left=sum_steps_left - 1)


def spec_to_high_level_code(task_spec, spec2highlevelcode_prompt, code_save_path):
    """
    Give a task specification {task_spec}, generate the corresponding high-level code

    Parameters:
        task_spec (str): detailed language instruction to generate the high-level code from
        spec2highlevelcode_prompt (dictionary): dictionary containing "main" and "examples" that defines the LLM prompt to 
            generate high-level code based on the task specification
        code_save_path (str): path to save the generated code
    """
    task_spec_query = task_spec.strip("\n").strip()

    if '"""' not in task_spec_query:
        task_spec_query = f'"""\n{task_spec_query}\n"""'
    
    if '```' not in task_spec_query:
        task_spec_query = f'```\n{task_spec_query}\n```'

    high_level_code = call_openai_api(main_prompt=spec2highlevelcode_prompt["main"].strip("\n").strip(), 
                                        raw_examples_list=spec2highlevelcode_prompt["examples"],
                                        user_query=task_spec_query.strip("\n").strip(), 
                                        stop_list=[],
                                        temperature=0.0,
                                        max_tokens=8000,
                                        gpt_model="gpt-3.5-turbo-16k")
    
    high_level_code = high_level_code.strip().strip('\n')
    
    if '```' in high_level_code:
        # remove the markdown code tag
        high_level_code = high_level_code.split('```')[1]

    high_level_code = high_level_code.strip().strip('\n')

    with open(code_save_path, "w") as fout:
        fout.write(high_level_code)

    # pretty-print the generated code
    cprint(high_level_code)


"""''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

    Helper functions

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''"""


def is_summarized(demos_list):
    """
    Return true if all demonstrations in the list are sufficiently summarized

    Parameters:
        demos_list (list): a list of demonstrations that are currently getting summarized

    Return:
        (bool)
    """
    for demo in demos_list:
        if "[[Summarized trajectory:]]" in demo and "[[Is the new trajectory sufficiently summarized? (yes/no):]]" in demo:
            _, _, rest = demo.partition("[[Is the new trajectory sufficiently summarized? (yes/no):]]\n")
            answer, _, _ = rest.partition("[[Summarized trajectory:]]")

            answer = answer.strip().strip("\n")

            if "no" in answer:
                return False
            else:
                continue
        elif "[[Input Trajectory:]]" in demo:
            # assume this is the initial demo from the user, so it's not summarized
            return False
        else:
            print("unable to extrat yes/no summariztion status from the output")
            print(demo)
            return False
        
    return True


def prepare_demo_query(demo):
    """
    Prepare the input demo for the LLM to summarize

    Parameters:
        demo (str): a demonstration to get formatted and prepared

    Return:
        (str)
    """
    if "[[Summarized trajectory:]]" in demo and "[[Is the new trajectory sufficiently summarized? (yes/no):]]" in demo:
        # during the recursive summarization process
        _, _, clean_demo = demo.partition("[[Summarized trajectory:]]\n")

        clean_demo = clean_demo.strip().strip('\n')

        clean_demo = f"[[Input Trajectory:]]\n{clean_demo}"

        return clean_demo
    elif "[[Input Trajectory:]]" in demo:
        # assume that the demo is already prepared, just return the demo
        return demo
    else:
        print("unable to extract summarized trajectory from the output")
        print(demo)
        assert False

def combine_all_demos(demos_list, lang_goal):
    """
    Concatenate the {lang_goal} and all demonstrations in the {demos_list} for the LLM

    Parameters:
        demos_list (list): a list of demonstrations that are currently getting summarized
        lang_goal (str): language describing the general goal of the task

    Return:
        (str)
    """
    if lang_goal != "":
        summary2spec_query = f"[[High-Level Goal:]]\n{lang_goal}\n[[Trajectories:]]"
    else:
        summary2spec_query = f"[[Trajectories:]]"

    for demo in demos_list:
        clean_demo = prepare_demo_query(demo)
        # normally the demo query contains the [[Input Trajectory:]] tag, so we also remove those
        _, _, clean_demo = clean_demo.partition("[[Input Trajectory:]]\n")

        clean_demo = clean_demo.strip("\n").strip()

        summary2spec_query = f"{summary2spec_query}\n{clean_demo}"

    return summary2spec_query.strip("\n").strip()

def clean_up_specification(spec):
    """
    Extract the specification from the LLM output
        remove all the extra tags and separators

    Parameters:
        spec (str): raw task specification generated by the LLM

    Return:
        (str)
    """
    if "[[Task Specification:]]" in spec and "[[end of response]]" in spec:
        _, _, after = spec.partition("[[Task Specification:]]\n")
         
        clean_spec, _, _ = after.partition("[[end of response]]")

        return clean_spec.strip("\n").strip()
    elif "[[Task Specification:]]" in spec:
        # if the LLM does not generate [[end of response]], 
        # we just assume that everything after [[Task Specification:]] to be a part of task spec
        _, _, clean_spec = spec.partition("[[Task Specification:]]\n")

        return clean_spec.strip("\n").strip()
    else:
        print("unable to extract task specification")
        print(spec)
        assert False



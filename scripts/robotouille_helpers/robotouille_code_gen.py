from overall_helper.lmp import call_openai_api
from overall_helper.utils import cprint


def robotouille_code_generator(lmp_name, task_name, query_config_basename, user_query, code_save_path="", cot_save_path=""):
    if "-prompt" in query_config_basename:
        query_config_basename_for_prompt = query_config_basename.replace("-prompt", "")
    else:
        query_config_basename_for_prompt = query_config_basename

    """
    [Stage 1: Recursive Summarization] for demonolang2code and demo2code
    """
    if "demo" in lmp_name:
        with open(f".{task_name}/prompts/{lmp_name}/{lmp_name}_{query_config_basename_for_prompt}-summary_prompt.txt", "r") as f_in:
            summary_prompt = f_in.read().strip()

        with open(f".{task_name}/prompts/{lmp_name}/{lmp_name}_{query_config_basename_for_prompt}-demo2spec_prompt.txt", "r") as f_in:
            demo2spec_prompt = f_in.read().strip()

        clean_query = user_query.replace('"""', "")
        clean_query = clean_query.strip("\n")

        """
        Extract all demos from the user query into a list
        """
        demos_list = []
        i = 1
        while f"[Scenario {i}]" in clean_query:
            before, _, after = clean_query.partition(f"[Scenario {i+1}]")

            # prepare the rest of the query for the next loop
            if f"[Scenario {i+1}]" in clean_query:
                clean_query = f"[Scenario {i+1}]{after}"
            else:
                clean_query = ""

            before_states, _, states = before.partition("State 2:")
            if i == 1:
                # if it's the first demo, we want to extract the high level goal
                _, _, lang_goal = before_states.partition(f"[Scenario {i}]\n")
                lang_goal = lang_goal.strip("\n")

            demo = f"[[Input Trajectory:]]\n[Scenario {i}]\nState 2:{states}"
            
            demos_list.append(demo)

            i += 1

        """
        Stage 1: Recursive Summarization
        """
        with open(cot_save_path, "w") as fout:
            fout.write("")

        task_spec = robotouille_summarize(demos_list, lang_goal, summary_prompt, demo2spec_prompt, cot_save_path)
    else:
        # if there is no demo provided, we use the user query
        task_spec = user_query

    """
    Task Specifcation -> High Level Code
    """
    if lmp_name == "lang2code":
        spec2highlevelcode_prompt_path = f".{task_name}/prompts/lang2code/lang2code_{query_config_basename_for_prompt}-spec2highlevelcode_prompt.txt"
    else:
        spec2highlevelcode_prompt_path = f".{task_name}/prompts/spec2code/spec2code_{query_config_basename_for_prompt}-spec2highlevelcode_prompt.txt"
    
    with open(spec2highlevelcode_prompt_path, "r") as f_in:
        spec2highlevelcode_prompt = f_in.read().strip()

    robotouille_spec_to_high_level_code(task_spec, spec2highlevelcode_prompt, code_save_path)

    # input("stop")


def robotouille_summarize(demos_list, lang_goal, summarize_prompt, demo2spec_prompt, cot_save_path):
    if robotouille_is_summarized(demos_list):
        all_demos = robotouille_combine_all_demos(demos_list, lang_goal)

        specification = call_openai_api(prompt=demo2spec_prompt.strip().strip("\n"), 
                                                    user_query=all_demos.strip().strip("\n"), 
                                                    has_header=True,
                                                    header_response_msg="",
                                                    stop_list=["[[end of response]]"],
                                                    temperature=0.0,
                                                    max_tokens=8000,
                                                    gpt_model="gpt-3.5-turbo-16k")
        
        with open(cot_save_path, "a") as fout:
            fout.write("==========================demo -> spec==========================\n")
            fout.write(specification)
            fout.write("\n\n")

        # remove intermediate reasoning and just return the task specification
        clean_specification = robotouille_clean_up_specification(specification)

        print("==========================demo -> spec==========================")
        print(clean_specification)
            
        return clean_specification
    else:
        summarized_demos_list = []
        for demo in demos_list:
            demo_query = robotouille_prepare_demo_query(demo)

            summarized_demo = call_openai_api(prompt=summarize_prompt.strip().strip("\n"), 
                                                    user_query=demo_query.strip().strip("\n"), 
                                                    has_header=True,
                                                    header_response_msg="",
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
            
        return robotouille_summarize(summarized_demos_list, lang_goal, summarize_prompt, demo2spec_prompt, cot_save_path)
        

def robotouille_is_summarized(demos_list):
    for demo in demos_list:
        if "[[Summarized trajectory:]]" in demo and "[[Is the new trajectory sufficiently summarized? (yes/no):]]" in demo:
            _, _, after = demo.partition("[[Is the new trajectory sufficiently summarized? (yes/no):]]\n")

            if "no" in after:
                return False
            else:
                continue
        else:
            print("unable to extrat yes/no summariztion status from the output")
            print(demo)
            return False
        
    return True


def robotouille_prepare_demo_query(demo):
    if "[[Summarized trajectory:]]" in demo and "[[Is the new trajectory sufficiently summarized? (yes/no):]]" in demo:
        _, _, after = demo.partition("[[Summarized trajectory:]]\n")

        clean_demo, _, _ = after.partition("[[Is the new trajectory sufficiently summarized? (yes/no):]]\n")

        clean_demo = clean_demo.strip().strip('\n')

        clean_demo = f"[[Input Trajectory:]]\n{clean_demo}"

        return clean_demo
    elif "[[Input Trajectory:]]" in demo:
        # assume that the demo is already prepared, just return the demo
        return demo
    else:
        print("unable to extract summarized trajectory from the output")
        print(demo)
        input("error")


def robotouille_combine_all_demos(demos_list, lang_goal):
    demo2spec_query = f"[[High-Level Goal:]]\n{lang_goal}\n[[High-Level Subtask Trajectories:]]"

    for demo in demos_list:
        clean_demo = robotouille_prepare_demo_query(demo)
        # normally the demo query contains the [[Input Trajectory:]] tag, so we also remove those
        _, _, clean_demo = clean_demo.partition("[[Input Trajectory:]]\n")

        clean_demo = clean_demo.strip().strip("\n")

        demo2spec_query = f"{demo2spec_query}\n{clean_demo}"

    return demo2spec_query.strip().strip("\n")
    

def robotouille_clean_up_specification(spec):
    if "[[Task Specification:]]" in spec and "[[end of response]]" in spec:
        _, _, after = spec.partition("[[Task Specification:]]\n")
         
        clean_spec, _, _ = after.partition("[[end of response]]")

        return clean_spec.strip().strip("\n")
    elif "[[Task Specification:]]" in spec:
        # if the LLM does not generate [[end of response]], 
        # we just assume that everything after [[Task Specification:]] to be a part of task spec
        _, _, clean_spec = spec.partition("[[Task Specification:]]\n")

        return clean_spec.strip().strip("\n")
    else:
        print("unable to extract task specification")
        print(spec)
        input("error")


def robotouille_spec_to_high_level_code(task_spec, spec2highlevelcode_prompt, code_save_path):
    task_spec_query = task_spec.strip().strip("\n")

    if '"""' not in task_spec_query:
        task_spec_query = f'"""\n{task_spec_query}\n"""'
    
    if '```' not in task_spec_query:
        task_spec_query = f'```\n{task_spec_query}\n```'

    high_level_code = call_openai_api(prompt=spec2highlevelcode_prompt.strip().strip("\n"), 
                                        user_query=task_spec_query.strip().strip("\n"), 
                                        has_header=True,
                                        header_response_msg="",
                                        stop_list=[],
                                        temperature=0.0,
                                        max_tokens=8000,
                                        gpt_model="gpt-3.5-turbo-16k")
    
    high_level_code = high_level_code.strip().strip('\n')
    
    if '```' in high_level_code:
        high_level_code = high_level_code.split('```')[1]

    high_level_code = high_level_code.strip().strip('\n')

    with open(code_save_path, "w") as fout:
        fout.write(high_level_code)

    cprint(high_level_code)
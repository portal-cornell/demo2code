import os

import openai
openai.api_key = os.environ["OPENAI_API_KEY"]

import ast
import astunparse
from shapely.geometry import *
from shapely.affinity import *
from time import sleep
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter
import traceback
import yaml

from scripts.overall_helpers.utils import *
from scripts.overall_helpers.openai_helper import call_openai_api

SUCCESS = 1
FAIL = 0
REDO = -1

class LMP:
    def __init__(self, name, cfg, fixed_vars, variable_vars, lmp_fgen=None, return_exec_status=False):
        self._name = name
        self._cfg = cfg

        self._base_prompt_dict = self._cfg['prompt_dict']

        self._stop_tokens = list(self._cfg['stop'])

        self._lmp_fgen = lmp_fgen

        self._fixed_vars = fixed_vars
        self._variable_vars = variable_vars
        self.exec_hist = ''

        self._return_exec_status = return_exec_status

    def clear_exec_hist(self):
        self.exec_hist = ''

    def build_prompt(self, query, context):      
        if self._base_prompt_dict != {}:
            prompt = self._base_prompt_dict["main"]
            examples = self._base_prompt_dict["examples"]
        else:
            prompt = ""
            examples = []

        user_query = f'{context}\n{self._cfg["query_prefix"]}{query}{self._cfg["query_suffix"]}'

        return prompt, examples, user_query

    def __call__(self, user_query='', context="", load_code_path='', **kwargs):
        prompt, examples, user_query = self.build_prompt(user_query, context)
        
        if load_code_path != '':
            with open(load_code_path, "r") as fin:
               code_str = fin.read()
        else:
            code_str = call_openai_api(main_prompt = prompt, 
                                       raw_examples_list = examples, 
                                       user_query = user_query,
                                        temperature=self._cfg['temperature'], stop_list=self._stop_tokens, max_tokens=self._cfg['max_tokens'])
            
        to_log = f'{user_query}\n{code_str}'
        cprint(to_log)

        if self._lmp_fgen:
            # if there is a function generating lmp
            new_fs = self._lmp_fgen.create_new_fs_from_code(code_str, step_num=2)
            self._variable_vars.update(new_fs)

        if self._cfg['include_context'] and context != '':
            to_exec = f'{context}\n{code_str}'
        else:
            to_exec = code_str
        
        gvars = merge_dicts([self._fixed_vars, self._variable_vars])
        lvars = kwargs

        status = SUCCESS
        try:
            exec_safe(to_exec, gvars, lvars)
        except ExecError:
            print("invalid env setup, retry process")
            status = REDO
        except MaxStepsError:
            print("maximum steps reached, retry process")
            status = FAIL
        except Exception:
            print("Executing the code failed")
            traceback.print_exc()
            status = FAIL

        self.exec_hist += f'\n{to_exec}'

        if self._cfg['has_return']:
            if self._return_exec_status:
                return lvars[self._cfg['return_val_name']], status
            else:
                return lvars[self._cfg['return_val_name']]
        
        if self._return_exec_status:
           return status


def get_clean_fsig(f_sig):
    """
    Return clean function signature that just has the parameter name
    """
    if "=" in f_sig:
        f_sig_list = f_sig.split("=")
        f_sig_clean = f_sig_list[0]
        for chunk in f_sig_list:
            if "," in chunk:
                _, _, arg = chunk.partition(",")
                arg = arg.strip()
                f_sig_clean = f"{f_sig_clean}, {arg}"
        return f"{f_sig_clean})", True
    else:
        return f_sig, False
    

class LMPFGen:
    """
    Adapted from CodeAsPolicies code base: https://github.com/google-research/google-research/tree/master/code_as_policies
    """
    def __init__(self, model_name, prompt_version, fixed_vars, variable_vars):
        self._prompt_version = prompt_version
        self._model_name = model_name

        self._stop_tokens = ['"""']
        self._fixed_vars = fixed_vars
        self._variable_vars = variable_vars

    def create_f_from_sig(self, f_name, f_sig, step_num, other_vars=None, fix_bugs=False, return_src=False):
        print(f'Creating function: {f_sig}')

        f_sig_clean, _ = get_clean_fsig(f_sig)
        f_name_as_a_file = f_sig_clean.strip()
        
        if not os.path.isfile(f"./outputs/robotouille/code/helper-functions/{self._prompt_version}/{f_name_as_a_file}_code.txt"):
            with open(f"./data/robotouille/prompts/{self._model_name}/{self._model_name}_prompt.yaml", "r") as fin:
                prompt_dict = yaml.safe_load(fin)

            if step_num == 2:
                requirement = '''You can use functions imported above and also call new functions

The robot might not be near any object or near any location specified in the function parameters.'''
            elif step_num == 3:
                requirement = '''You can only use the functions imported in the header.'''
            else:
                print(step_num)
                print("<<invalid step_num>>")
                assert False

            user_query = f'```\n"""\n{requirement}\n\nDefine the function: {f_sig_clean}\n"""\n```'

            code_prompt = prompt_dict["stage2"]["recursive_expansion"][f"step{step_num}"]["main"]
            code_prompt_examples = prompt_dict["stage2"]["recursive_expansion"][f"step{step_num}"]["examples"]

            f_src = call_openai_api(main_prompt = code_prompt, 
                                    raw_examples_list= code_prompt_examples,
                                    user_query=user_query,
                                    temperature=0, 
                                    stop_list=self._stop_tokens, 
                                    max_tokens=600,
                                    gpt_model="gpt-3.5-turbo-16k")
            
            if '```' in f_src:
                # remove the markdown code tag
                f_src = f_src.split('```')[1]

            f_src = f_src.strip().strip('\n')
            
            with open(f"./outputs/robotouille/code/helper-functions/{self._prompt_version}/{f_name_as_a_file}_code.txt", "w") as fout:
                fout.write(f_src)
        else:
            with open(f"./outputs/robotouille/code/helper-functions/{self._prompt_version}/{f_name_as_a_file}_code.txt", "r") as fin:
                f_src = fin.read()
            
        if other_vars is None:
            other_vars = {}
        gvars = merge_dicts([self._fixed_vars, self._variable_vars, other_vars])
        lvars = {}
        
        exec_safe(f_src, gvars, lvars)

        f = lvars[f_name]

        to_print = highlight(f'{f_src}', PythonLexer(), TerminalFormatter())
        print(f'LMP FGEN created:\n\n{to_print}\n')

        if return_src:
            return f, f_src
        return f

    def create_new_fs_from_code(self, code_str, step_num, other_vars=None, fix_bugs=False, return_src=False):
        fs, f_assigns = {}, {}
        f_parser = FunctionParser(fs, f_assigns)
        f_parser.visit(ast.parse(code_str))
        for f_name, f_assign in f_assigns.items():
            if f_name in fs:
                fs[f_name] = f_assign

        if other_vars is None:
            other_vars = {}

        new_fs = {}
        srcs = {}
        
        for f_name, f_sig in fs.items():
            all_vars = merge_dicts([self._fixed_vars, self._variable_vars, new_fs, other_vars])

            if not var_exists(f_name, all_vars):
                f, f_src = self.create_f_from_sig(f_name, f_sig, step_num, 
                                                  other_vars=new_fs, fix_bugs=fix_bugs, return_src=True)

                # recursively define child_fs in the function body if needed
                f_def_body = astunparse.unparse(ast.parse(f_src).body[0].body)
                child_fs, child_f_srcs = self.create_new_fs_from_code(
                    f_def_body, step_num=step_num+1, 
                    other_vars=all_vars, fix_bugs=fix_bugs, return_src=True
                )
            
                if len(child_fs) > 0:
                    new_fs.update(child_fs)
                    srcs.update(child_f_srcs)

                    # redefine parent f so newly created child_fs are in scope
                    gvars = merge_dicts([self._fixed_vars, self._variable_vars, new_fs, other_vars])
                    lvars = {}
                    
                    exec_safe(f_src, gvars, lvars)

                    f = lvars[f_name]

                new_fs[f_name], srcs[f_name] = f, f_src

        if return_src:
            return new_fs, srcs
        return new_fs


class FunctionParser(ast.NodeTransformer):

    def __init__(self, fs, f_assigns):
        super().__init__()
        self._fs = fs
        self._f_assigns = f_assigns

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name):
            f_sig = astunparse.unparse(node).strip()
            f_name = astunparse.unparse(node.func).strip()
            self._fs[f_name] = f_sig
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        if isinstance(node.value, ast.Call):
            assign_str = astunparse.unparse(node).strip()
            f_name = astunparse.unparse(node.value.func).strip()
            self._f_assigns[f_name] = assign_str
        return node


def var_exists(name, all_vars):
    try:
        eval(name, all_vars)
    except:
        exists = False
    else:
        exists = True
    return exists


def merge_dicts(dicts):
    return {
        k : v 
        for d in dicts
        for k, v in d.items()
    }
    

def exec_safe(code_str, gvars=None, lvars=None):
    banned_phrases = ['import', '__']
    for phrase in banned_phrases:
        assert phrase not in code_str
  
    if gvars is None:
        gvars = {}
    if lvars is None:
        lvars = {}
    empty_fn = lambda *args, **kwargs: None
    custom_gvars = merge_dicts([
        gvars,
        {'exec': empty_fn, 'eval': empty_fn}
    ])
    exec(code_str, custom_gvars, lvars)

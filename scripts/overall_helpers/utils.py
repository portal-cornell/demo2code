import os

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter

def safe_mkdir(dir_relative_path):
    if not os.path.exists(dir_relative_path):
        os.mkdir(dir_relative_path)


def cprint(code_str):
  print(highlight(code_str, PythonLexer(), TerminalFormatter()))

def convert_str_to_list(list_in):
    if type(list_in) == str:
        if ', ' in list_in:
            splitted_string = list_in.strip('][').split(', ')
        else:
            splitted_string = list_in.strip('][').split(',')
            
        return [w[1:-1] for w in splitted_string]
    else:
        return list_in
    
def convert_int_list_str_to_list(list_in):
    if type(list_in) == str:
        if ', ' in list_in:
            splitted_string = list_in.strip('][').split(', ')
        else:
            splitted_string = list_in.strip('][').split(',')
            
        return [int(w) for w in splitted_string]
    else:
        return list_in
    
class ExecError(Exception):
    pass

class MaxStepsError(Exception):
    pass
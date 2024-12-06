"""
Adapted from CodeAsPolicies code base: https://github.com/google-research/google-research/tree/master/code_as_policies
"""

model_cfg_all = {
    'spec2code': {
      'prompt_dict': {},
      'max_tokens': 512,
      'temperature': 0,
      'query_prefix': '',
      'query_suffix': '',
      'stop': ['"""', 'objects=['],
      'debug_mode': False,
      'include_context': True,
      'has_return': False
    },
    'lang2code': {
      'prompt_dict': {},
      'max_tokens': 512,
      'temperature': 0,
      'query_prefix': '',
      'query_suffix': '',
      'stop': ['"""', 'objects=['],
      'debug_mode': False,
      'include_context': True,
      'has_return': False
    },
    'demonolang2code': {
      'prompt_dict': {},
      'max_tokens': 512,
      'temperature': 0,
      'query_prefix': '',
      'query_suffix': '',
      'stop': ['"""', 'objects=['],
      'include_context': True,
      'has_return': False
    },
    'demo2code': {
      'prompt_dict': {},
      'max_tokens': 512,
      'temperature': 0,
      'query_prefix': '',
      'query_suffix': '',
      'stop': ['"""', 'objects=['],
      'include_context': True,
      'has_return': False
    }
}
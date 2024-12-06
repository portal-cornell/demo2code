import yaml

with open("./data/tabletop/prompt/helper/prompt_parse_obj_name.yaml", "r") as fin:
    prompt_parse_obj_name = yaml.safe_load(fin)

with open("./data/tabletop/prompt/helper/prompt_parse_position.yaml", "r") as fin:
    prompt_parse_position = yaml.safe_load(fin)

helper_lmp_cfg= {
  'lmps': {
    'parse_obj_name': {
      'prompt_dict': prompt_parse_obj_name,
      'engine': 'gpt-3.5-turbo',
      'max_tokens': 512,
      'temperature': 0,
      'query_prefix': '# ',
      'query_suffix': '.',
      'stop': ['#', 'objects=['],
      'include_context': True,
      'has_return': True,
      'return_val_name': 'ret_val',
    },
    'parse_position': {
      'prompt_dict': prompt_parse_position,
      'engine': 'gpt-3.5-turbo',
      'max_tokens': 512,
      'temperature': 0,
      'query_prefix': '# ',
      'query_suffix': '.',
      'stop': ['#'],
      'include_context': True,
      'has_return': True,
      'return_val_name': 'ret_val',
    }
  }
}
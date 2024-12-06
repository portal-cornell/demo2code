
robotouille_prompt_template = {
    ##############
    # BASE TASKS #
    ##############
    'base-move': {
        'command': "Move to <loc_1>.",
        'unit_tests': {
            'none': ['loc(robot1:player,<p-loc_1>:station):1']
        }
    },
    'base-pickup': {
        'command': "Pick up <obj_1>.",
        'unit_tests': {
            'none': ['at(<obj_1>:item,<o-loc_1>:station):0', 'has(robot1:player,<obj_1>:item):1']
        }
    },
    'base-place': {
        'command': "Place <obj_1> on <loc_1>.",
        'unit_tests': {
            'none': ['at(<obj_1>:item,<p-loc_1>:station):1', 'has(robot1:player,<obj_1>:item):0']
        }
    },
    'base-cut': {
        'command': "Cut <obj_1>.",
        'unit_tests': {
            'none': ['iscut(<obj_1>:item):1']
        }
    },
    'base-cook': {
        'command': "Cook <obj_1>.",
        'unit_tests': {
            'none': ['iscooked(<obj_1>:item):1']
        }
    },
    'base-stack': {
        'command': "Stack <obj_1> on top of <obj_2>.",
        'unit_tests': {
            'none': ['atop(<obj_1>:item,<obj_2>:item):1', 'has(robot1:player,<obj_1>:item):0']
        }
    },
    'base-unstack': {
        'command': "Unstack <obj_1> from <obj_2>.",
        'unit_tests': {
            'none': ['atop(<obj_1>:item,<obj_2>:item):0', 'has(robot1:player,<obj_1>:item):1']
        }
    },
    ###################
    # COMPOSITE TASKS #
    ###################
    'composite-move-pickup': {
        'command': 'Pick up <obj_1>.',
        'descriptions': {
            # example of how you can differentiate language instruction between very specific and vague
            'specific': "Move to <loc_1> then pick up <obj_1>.",
            'vague': "Pick up <obj_1>."  # the LLM need to figure out from state transition that it moved then picked
        },
        'unit_tests': {
            'none': ['loc(robot1:player,<o-loc_1>:station):1', 'at(<obj_1>:item,<o-loc_1>:station):0', 'has(robot1:player,<obj_1>:item):1']
        }
    },
    'composite-move-place': {
        'command': 'Place <obj_1> on <loc_1>.',
        'descriptions': {
            # example of how you can differentiate language instruction between very specific and vague
            'specific': "Move to <loc_1> then place down <obj_1>.",
            'vague': "Place <obj_1> at <loc_1>."  # the LLM need to figure out from state transition that it moved then picked
        },
        'unit_tests': {
            'none': ['loc(robot1:player,<p-loc_1>:station):1', 'at(<obj_1>:item,<p-loc_1>:station):1', 'has(robot1:player,<obj_1>:item):0']
        }
    },
    'composite-move-cut': {
        'command': 'Cut <obj_1>.',
        'unit_tests': {
            'none': ['loc(robot1:player,<o-loc_1>:station):1', 'iscut(<obj_1>:item):1']
        }
    },
    'composite-move-cook': {
        'command': 'Cook <obj_1>.',
        'unit_tests': {
            'none': ['loc(robot1:player,<o-loc_1>:station):1', 'iscooked(<obj_1>:item):1']
        }
    },
    'composite-move-stack': {
        'command': "Stack <obj_1> on top of <obj_2>.",
        'unit_tests': {
            'none': ['loc(robot1:player,<o-loc_2>:station):1', 'atop(<obj_1>:item,<obj_2>:item):1', 'has(robot1:player,<obj_1>:item):0']
        }
    },
    'composite-move-unstack': {
        'command': "Unstack <obj_1> from <obj_2>.",
        'unit_tests': {
            'none': ['loc(robot1:player,<o-loc_2>:station):1', 'atop(<obj_1>:item,<obj_2>:item):0', 'has(robot1:player,<obj_1>:item):1']
        }
    },
    'composite-cut-pickup': {
        'command': 'Cut then pick up <obj_1>.',
        'unit_tests': {
            'none': ['iscut(<obj_1>:item):1', 'at(<obj_1>:item,<o-loc_1>:station):0', 'has(robot1:player,<obj_1>:item):1']
        }
    },
    'composite-cook-pickup': {
        'command': 'Cook then pick up <obj_1>.',
        'unit_tests': {
            'none': ['iscooked(<obj_1>:item):1', 'at(<obj_1>:item,<o-loc_1>:station):0', 'has(robot1:player,<obj_1>:item):1']
        }
    },
    'composite-place-cut': {
        'command': 'Place then cut <obj_1> on <loc_1>.',
        'unit_tests': {
            'none': ['at(<obj_1>:item,<p-loc_1>:station):1', 'has(robot1:player,<obj_1>:item):0', 'iscut(<obj_1>:item):1']
        },
    },
    'composite-place-cook': {
        'command': 'Place then cook <obj_1> on <loc_1>.',
        'unit_tests': {
            'none': ['at(<obj_1>:item,<p-loc_1>:station):1', 'has(robot1:player,<obj_1>:item):0', 'iscooked(<obj_1>:item):1']
        }
    },
    ####################
    # HIGH LEVEL TASKS #
    ####################
    'high-level-cook-and-cut': {
        'command': 'Cook a patty and cut a lettuce.',
        'unit_tests': {
            'cook-first': ['iscooked\(patty([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1'],
            'cut-first': ['iscut\(lettuce([0-9]+):item\):1', 'iscooked\(patty([0-9]+):item\):1'],
            'cook-only': ['iscooked\(patty([0-9]+):item\):1'],
            'cut-only': ['iscut\(lettuce([0-9]+):item\):1']
        }
    },
    'high-level-lettuce-burger': {
        'command': 'Make a burger.',
        'unit_tests': {
            'lettuce-only': ['iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<0>:item,bottombun([0-9]+):item\):1', 'atop\(topbun([0-9]+):item,lettuce<0>:item\):1'],
            'stack-immediate-lettuce-patty': ['iscooked\(patty([0-9]+):item\):1', 'atop\(patty<0>:item,bottombun([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<2>:item,patty<0>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<2>:item\):1'],
            'stack-immediate-patty-lettuce': ['iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<0>:item,bottombun([0-9]+):item\):1', 'iscooked\(patty([0-9]+):item\):1', 'atop\(patty<2>:item,lettuce<0>:item\):1', 'atop\(topbun([0-9]+):item,patty<2>:item\):1'],
            'stack-last-lettuce-patty': [('iscooked\(patty([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1'), 'atop\(patty<0>:item,bottombun([0-9]+):item\):1', 'atop\(lettuce<1>:item,patty<0>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<1>:item\):1'],
            'stack-last-patty-lettuce': [('iscut\(lettuce([0-9]+):item\):1', 'iscooked\(patty([0-9]+):item\):1'), 'atop\(lettuce<0>:item,bottombun([0-9]+):item\):1', 'atop\(patty<1>:item,lettuce<0>:item\):1', 'atop\(topbun([0-9]+):item,patty<1>:item\):1'],
            'substitute-cheese': ['iscooked\(patty([0-9]+):item\):1', 'atop\(patty<0>:item,bottombun([0-9]+):item\):1', 'atop\(cheese([0-9]+):item,patty<0>:item\):1', 'atop\(topbun([0-9]+):item,cheese<2>:item\):1'],
            'substitute-onions': ['iscooked\(patty([0-9]+):item\):1', 'atop\(patty<0>:item,bottombun([0-9]+):item\):1',  'iscut\(onion([0-9]+):item\):1', 'atop\(onion<2>:item,patty<0>:item\):1', 'atop\(topbun([0-9]+):item,onion<2>:item\):1'],
            'substitute-chicken': ['iscooked\(chicken([0-9]+):item\):1', 'atop\(chicken<0>:item,bottombun([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<2>:item,chicken<0>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<2>:item\):1'],
            'add-tomato': ['iscooked\(patty([0-9]+):item\):1', 'atop\(patty<0>:item,bottombun([0-9]+):item\):1', 'iscut\(tomato([0-9]+):item\):1', 'atop\(tomato<2>:item,patty<0>:item\):1', 'iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<4>:item,tomato<2>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<4>:item\):1'],
        }
    },
    'high-level-two-lettuce-burger': {
        'command': 'Make two burgers.',
        'unit_tests': {
            'stack-immediate-lettuce-patty': ['iscooked\(patty([0-9]+):item\):1', 'atop\(patty<0>:item,bottombun([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<2>:item,patty<0>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<2>:item\):1', 'iscooked\(patty([0-9]+):item\):1', 'atop\(patty<5>:item,bottombun([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<7>:item,patty<5>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<7>:item\):1'],
            'stack-immediate-patty-lettuce': ['iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<0>:item,bottombun([0-9]+):item\):1', 'iscooked\(patty([0-9]+):item\):1', 'atop\(patty<2>:item,lettuce<0>:item\):1', 'atop\(topbun([0-9]+):item,patty<2>:item\):1', 'iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<5>:item,bottombun([0-9]+):item\):1', 'iscooked\(patty([0-9]+):item\):1', 'atop\(patty<7>:item,lettuce<5>:item\):1', 'atop\(topbun([0-9]+):item,patty<7>:item\):1'],
            'stack-last-lettuce-patty': [('iscooked\(patty([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1'), 'atop\(patty<0>:item,bottombun([0-9]+):item\):1', 'atop\(lettuce<1>:item,patty<0>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<1>:item\):1', ('iscooked\(patty([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1'), 'atop\(patty<5>:item,bottombun([0-9]+):item\):1', 'atop\(lettuce<6>:item,patty<5>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<6>:item\):1'],
            'stack-last-patty-lettuce': [('iscut\(lettuce([0-9]+):item\):1', 'iscooked\(patty([0-9]+):item\):1'), 'atop\(lettuce<0>:item,bottombun([0-9]+):item\):1', 'atop\(patty<1>:item,lettuce<0>:item\):1', 'atop\(topbun([0-9]+):item,patty<1>:item\):1', ('iscut\(lettuce([0-9]+):item\):1', 'iscooked\(patty([0-9]+):item\):1'), 'atop\(lettuce<5>:item,bottombun([0-9]+):item\):1', 'atop\(patty<6>:item,lettuce<5>:item\):1', 'atop\(topbun([0-9]+):item,patty<6>:item\):1'],
            'substitute-cheese': ['iscooked\(patty([0-9]+):item\):1', 'atop\(patty<0>:item,bottombun([0-9]+):item\):1', 'atop\(cheese([0-9]+):item,patty<0>:item\):1', 'atop\(topbun([0-9]+):item,cheese<2>:item\):1', 'iscooked\(patty([0-9]+):item\):1', 'atop\(patty<4>:item,bottombun([0-9]+):item\):1', 'atop\(cheese([0-9]+):item,patty<4>:item\):1', 'atop\(topbun([0-9]+):item,cheese<6>:item\):1'],
            'substitute-onions': ['iscooked\(patty([0-9]+):item\):1', 'atop\(patty<0>:item,bottombun([0-9]+):item\):1',  'iscut\(onion([0-9]+):item\):1', 'atop\(onion<2>:item,patty<0>:item\):1', 'atop\(topbun([0-9]+):item,onion<2>:item\):1', 'iscooked\(patty([0-9]+):item\):1', 'atop\(patty<5>:item,bottombun([0-9]+):item\):1',  'iscut\(onion([0-9]+):item\):1', 'atop\(onion<7>:item,patty<5>:item\):1', 'atop\(topbun([0-9]+):item,onion<7>:item\):1'],
            'substitute-chicken': ['iscooked\(chicken([0-9]+):item\):1', 'atop\(chicken<0>:item,bottombun([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<2>:item,chicken<0>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<2>:item\):1', 'iscooked\(chicken([0-9]+):item\):1', 'atop\(chicken<5>:item,bottombun([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<7>:item,chicken<5>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<7>:item\):1'],
            'add-tomato': ['iscooked\(patty([0-9]+):item\):1', 'atop\(patty<0>:item,bottombun([0-9]+):item\):1', 'iscut\(tomato([0-9]+):item\):1', 'atop\(tomato<2>:item,patty<0>:item\):1', 'iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<4>:item,tomato<2>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<4>:item\):1', 'iscooked\(patty([0-9]+):item\):1', 'atop\(patty<7>:item,bottombun([0-9]+):item\):1', 'iscut\(tomato([0-9]+):item\):1', 'atop\(tomato<9>:item,patty<7>:item\):1', 'iscut\(lettuce([0-9]+):item\):1', 'atop\(lettuce<11>:item,tomato<9>:item\):1', 'atop\(topbun([0-9]+):item,lettuce<11>:item\):1'],
            'cook-patties': ['iscooked\(patty([0-9]+):item\):1', 'iscooked\(patty([0-9]+):item\):1'],
            'cut-lettuces': ['iscut\(lettuce([0-9]+):item\):1', 'iscut\(lettuce([0-9]+):item\):1'],
        }
    },
    'high-level-assemble-burgers': {
        'command': 'Make two burgers. Because there are already a stack of two cooked patties, use them to make the burgers.',
        'unit_tests': {
            'none': ['atop\(patty([0-9]+):item,bottombun([0-9]+):item\):1', 'atop\(topbun([0-9]+):item,patty<0>:item\):1', 'atop\(patty([0-9]+):item,bottombun([0-9]+):item\):1', 'atop\(topbun([0-9]+):item,patty<2>:item\):1'],
            'parallel': [('atop\(patty([0-9]+):item,bottombun([0-9]+):item\):1', 'atop\(patty([0-9]+):item,bottombun([0-9]+):item\):1'), ('atop\(topbun([0-9]+):item,patty<0>:item\):1', 'atop\(topbun([0-9]+):item,patty<1>:item\):1')],
        }
    },
}

predicates_to_lang = {
    "loc": "'<1>' is <true>at '<2>'",
    "at": "'<1>' is <true>at '<2>'",
    "has": "'<1>' is <true>holding '<2>'",
    "iscooked": "'<1>' is <true>cooked",
    "atop": "'<1>' is <true>on top of '<2>'",
    "iscut": "'<1>' is <true>cut",
}
prompt_template = {
    'basic-place': {
        'num_objs': 2,
        'descriptions': 'Place the <obj_1> on the <obj_2>.',
        'code': '''put_first_on_second('<obj_1>', '<obj_2>')'''},
    'place-next-to': {
        'num_objs': 2,
        'descriptions': {
            'none': 'Place the <obj_1> next to the <obj_2>.',
            'none-specific': 'Place the <obj_1> at anywhere next to the <obj_2>.',
            'left': 'Place the <obj_1> to the left of the <obj_2>.',
            'right': 'Place the <obj_1> to the right of the <obj_2>.',
            'behind': 'Place the <obj_1> behind the <obj_2>.',
            'front': 'Place the <obj_1> in front of the <obj_2>.'
        },
        'code': {
            'none': '''position_relation = np.random.choice(ALL_POSITION_RELATION_LIST)
location_pos = parse_position(f'{position_relation} the <obj_2>')
put_first_on_second('<obj_1>', location_pos)''',
            'left': '''location_pos = parse_position('left of the <obj_2>')
put_first_on_second('<obj_1>', location_pos)''',
            'behind': '''location_pos = parse_position('behind the <obj_2>')
put_first_on_second('<obj_1>', location_pos)'''
        },
        'code_with-say': {
            'none': '''say("Place the <obj_1> at anywhere next to the <obj_2>.")
position_relation = np.random.choice(ALL_POSITION_RELATION_LIST)
location_pos = parse_position(f'{position_relation} the <obj_2>')
put_first_on_second('<obj_1>', location_pos)''',
            'left': '''say("Place the <obj_1> to the left of the <obj_2>.")
location_pos = parse_position('left of the <obj_2>')
put_first_on_second('<obj_1>', location_pos)''',
            'behind': '''say("Place the <obj_1> behind the <obj_2>.")
location_pos = parse_position('behind the <obj_2>')
put_first_on_second('<obj_1>', location_pos)'''
        },
        'unit_tests': {
            'none': [],
            'left': ['is_left_of:<obj_1>,<obj_2>:1'],
            'right': ['is_right_of:<obj_1>,<obj_2>:1'],
            'behind': ['is_behind:<obj_1>,<obj_2>:1'],
            'front': ['is_in_front_of:<obj_1>,<obj_2>:1']
        },
        'keywords_tests': {
            'none': ["np.random.choice(ALL_POSITION_RELATION_LIST)", "put_first_on_second('<obj_1>'"],
            'left': ["left of the", "put_first_on_second('<obj_1>'"],
            'right': ["right of the", "put_first_on_second('<obj_1>'"],
            'behind': ["behind the", "put_first_on_second('<obj_1>'"],
            'front': ["front of the", "put_first_on_second('<obj_1>'"]
        }
    },
    'place-at-corner':{
        'num_objs': 1,
        'descriptions': {
            'none': 'Place the <obj_1> at the corner.',
            'none-specific': 'Place the <obj_1> at any random corner.',
            'top-left': 'Place the <obj_1> at the top left corner.',
            'top-right': 'Place the <obj_1> at the top right corner.',
            'bottom-left': 'Place the <obj_1> at the bottom left corner.',
            'bottom-right': 'Place the <obj_1> at the bottom right corner.'
        },
        'code': {
            'none': '''corner_name = np.random.choice(ALL_CORNERS_LIST)
corner_pos = parse_position(corner_name)
put_first_on_second('<obj_1>', corner_pos)'''
        },
        'code_with-say': {
            'none': '''say("Place the <obj_1> at any random corner.")
corner_name = np.random.choice(ALL_CORNERS_LIST)
corner_pos = parse_position(corner_name)
put_first_on_second('<obj_1>', corner_pos)'''
        },
        'unit_tests': {
            'none': [],
            'top-left': ['is_at:<obj_1>,top left corner:1'],
            'top-right': ['is_at:<obj_1>,top right corner:1'],
            'bottom-left': ['is_at:<obj_1>,bottom left corner:1'],
            'bottom-right': ['is_at:<obj_1>,bottom right corner:1']
        },
        'keywords_tests': {
            'none': ["np.random.choice(ALL_CORNERS_LIST)"],
            'top-left': ["top left corner"],
            'top-right': ["top right corner"],
            'bottom-left': ["bottom left corner"],
            'bottom-right': ["bottom right corner"]
        }
    },
    'place-at-edge':{
        'num_objs': 1,
        'descriptions': {
            'none': 'Place the <obj_1> at the edge.',
            'none-specific': 'Place the <obj_1> at any random edge.',
            'top': 'Place the <obj_1> at the top edge.',
            'bottom': 'Place the <obj_1> at the bottom edge.',
            'left': 'Place the <obj_1> at the left edge.',
            'right': 'Place the <obj_1> at the right edge.',
        },
        'unit_tests': {
            'none': [],
            'top': ['is_at:<obj_1>,top edge:1'],
            'bottom': ['is_at:<obj_1>,bottom edge:1'],
            'left': ['is_at:<obj_1>,left edge:1'],
            'right': ['is_at:<obj_1>,right edge:1']
        },
        'keywords_tests': {
            'none': ["np.random.choice(ALL_EDGES_LIST)"],
            'top': ["top edge"],
            'bottom': ["bottom edge"],
            'left': ["left edge"],
            'right': ["right edge"]
        }
    },
    'place-on-hidden':{
        'num_objs': 5,  # at most there can be 5 objects
        'descriptions': {
            'none': 'Place the <obj_1> on the <obj_2>.',
            'none-specific': 'Directly place the <obj_1> on the <obj_2>.',
            '1-on-obj1': 'Place the <obj_1> on the <obj_2>. However, <obj_3> is on the <obj_1>. Thus, do the following steps:\n\
1. place the <obj_3> on the table\n\
2. place the <obj_1> on the <obj_2>',
            '2-on-obj1': 'Place the <obj_1> on the <obj_2>. However, the <obj_4> then the <obj_3> are on the <obj_1>. Thus, do the following steps:\n\
2. place the <obj_4> on the table\n\
3. place the <obj_3> on the table\n\
4. place the <obj_1> on the <obj_2>',
            '3-on-obj1': 'Place the <obj_1> on the <obj_2>. However, the <obj_5> then the <obj_4> then the <obj_3> are on the <obj_1>. Thus, do the following steps:\n\
1. place the <obj_5> on the table\n\
2. place the <obj_4> on the table\n\
3. place the <obj_3> on the table\n\
4. place the <obj_1> on the <obj_2>'
        },
        'code_with-say': {
            'none': '''say("Directly place the <obj_1> on the <obj_2>.")
put_first_on_second('<obj_1>', '<obj_2>')''',
            '3-on-obj1':'''say("First, place the <obj_5>, the <obj_4>, then the <obj_3> on the table. Then, place the <obj_1> on the <obj_2>.")
items_to_place_first_in_order = ['<obj_5>', '<obj_4>', '<obj_3>']
for item in items_to_place_first_in_order:
    put_first_on_second(item, "table")
put_first_on_second('<obj_1>', '<obj_2>')'''
        },
        'unit_tests':{
            'none': ['on_top_of:<obj_1>,<obj_2>:1','on_top_of:<obj_1>,table:0'],
            '1-on-obj1': ['on_top_of:<obj_1>,<obj_2>:1','on_top_of:<obj_1>,table:0','on_top_of:<obj_3>,<obj_1>:0','on_top_of:<obj_3>,table:1', ],
            '2-on-obj1': ['on_top_of:<obj_1>,<obj_2>:1','on_top_of:<obj_1>,table:0','on_top_of:<obj_3>,<obj_1>:0','on_top_of:<obj_3>,table:1', 'on_top_of:<obj_4>,<obj_1>:0','on_top_of:<obj_4>,table:1'],
            '3-on-obj1': ['on_top_of:<obj_1>,<obj_2>:1','on_top_of:<obj_1>,table:0','on_top_of:<obj_3>,<obj_1>:0','on_top_of:<obj_3>,table:1', 'on_top_of:<obj_4>,<obj_1>:0','on_top_of:<obj_4>,table:1', 'on_top_of:<obj_5>,<obj_1>:0','on_top_of:<obj_5>,table:1'],
        }
    },
    'stack-all-type':{
        'num_objs': 0, # this is not really useful
        'descriptions': {
            'none': "Stack all <type>s.",
            'none-specific': "Stack all <type>s, and the stack doesn't have a maximum height limit.",
            'max-2': "Stack all <type>s. However, the maximum height of a stack is 2.",
            'max-3': "Stack all <type>s. However, the maximum height of a stack is 3.",
            'max-4': "Stack all <type>s. However, the maximum height of a stack is 4.",
        },
        'code_with-say': {
            'none': '''say("Stack all <type>s into one stack.")
<type>_names = get_all_obj_names_that_match_type(type_name="<type>", objects_list=get_obj_names())
stack_without_height_limit(objects_to_stack=<type>_names)''',
            'max-3': '''say("Stack all <type>s into multiple stacks while making sure that each stack is at most 3 <type>s high.")
<type>_names = get_all_obj_names_that_match_type(type_name="<type>", objects_list=get_obj_names())
stack_with_height_limit(objects_to_stack=<type>_names, height_limit=3)'''
        },
        'code_with-say_cot':{
            'none': '''say("Stack all <type>s.")
say("Based on the states, stack 1 from bottom to top is: <stack_1>.")
say("Because there is only 1 stack, we assume that we can stack all blocks into one stack.")
<type>_names = get_all_obj_names_that_match_type(type_name="<type>", objects_list=get_obj_names())
stack_without_height_limit(objects_to_stack=<type>_names)''',
            'max-3': '''say("Stack all <type>s.")
say("Based on the states, stack 1 from bottom to top: <stack_1>.")
say("Based on the states, stack 2 from bottom to top: <stack_2>.")
say("Because there are 2 stacks and the first stack is 3 block high, we stack all blocks into multiple stacks while making sure that each stack is at most 3 blocks high.")
<type>_names = get_all_obj_names_that_match_type(type_name="<type>", objects_list=get_obj_names())
stack_with_height_limit(objects_to_stack=<type>_names, height_limit=3)'''
        }
    },
    'stack-all-type-order':{
        'num_objs': 0, # this is not really useful
        'descriptions':{
            'none': "Stack all <type>s into one stack.",
            'none-specific': "Stack all <type>s into one stack, and the order doesn't matter.",
            'partial-order-btw-2': "Stack all <type>s into one stack. Make sure that <obj_2> is always directly on top of <obj_1>.",
            'partial-order-btw-3': "Stack all <type>s into one stack. Make sure that <obj_3> is always directly on top of <obj_2>, and <obj_2> is always directly on top of <obj_1>.",
            'fully-ordered': "Stack all <type>s into one stack. Make sure that the <type>s are stacked in the following order from bottom to top: <stack_1>"
        },
        'code_with-say':{
            'none': '''say("Stack all <type>s into one stack, and the order doesn't matter.")
<type>_names = get_all_obj_names_that_match_type(type_name="<type>", objects_list=get_obj_names())
# Randomize the stack order since the order doesn't matter
np.random.shuffle(<type>_names)
stack_without_height_limit(objects_to_stack=<type>_names)''',
            'partial-order-btw-3': '''say("Stack all <type>s into one stack. Make sure that <obj_3> is always directly on top of <obj_2>, and <obj_2> is always directly on top of <obj_1>.")
# Based on the instruction, first define the <type>s that have strict ordering
<type>_names_with_strick_order_from_bottom_to_top = ['<obj_1>', '<obj_2>', '<obj_3>']
# Then, find the rest of the <type>s that don't have strict order
<type>_names = get_all_obj_names_that_match_type(type_name="<type>", objects_list=get_obj_names())
<type>_names_without_order = []
for <type> in <type>_names:
    if <type> not in <type>_names_with_strick_order_from_bottom_to_top:
        <type>_names_without_order.append(<type>)
# Call helper function to determine the final stacking order before stacking the <type>s
stack_order_from_bottom_to_top = determine_final_stacking_order(objects_to_enforce_order=<type>_names_with_strick_order_from_bottom_to_top, objects_without_order=<type>_names_without_order)
stack_without_height_limit(objects_to_stack=stack_order_from_bottom_to_top)''',
            'fully-ordered': '''say("Stack all <type>s into one stack. Make sure that the <type>s are stacked in the following order from bottom to top: <stack_1>")
# Because all the orders have been specified, stack all <type>s based on that order
stack_order_from_bottom_to_top = <stack_1>
stack_without_height_limit(objects_to_stack=stack_order_from_bottom_to_top)'''
        },
        'code_with-say_cot':{
            'partial-order-btw-3': '''say("Stack all <type>s into one stack.")
say("There are 2 scenarios: [Scenario 1] and [Scenario 2].")
say("Based on [Scenario 1]'s states, listing the <type>s in the stack from bottom to top: []")
say("Based on [Scenario 2]'s states, listing the <type>s in the stack from bottom to top: []")
say("The ordering that stays the same in both scenarios is: ['<obj_1>', '<obj_2>', '<obj_3>'], so these <type>s have strict ordering")
# Based on the instruction, first define the <type>s that have strict ordering
<type>_names_with_strick_order_from_bottom_to_top = ['<obj_1>', '<obj_2>', '<obj_3>']
# Then, find the rest of the <type>s that don't have strict order
<type>_names = get_all_obj_names_that_match_type(type_name="<type>", objects_list=get_obj_names())
<type>_names_without_order = []
for <type> in <type>_names:
    if <type> not in <type>_names_with_strick_order_from_bottom_to_top:
        <type>_names_without_order.append(<type>)
# Call helper function to determine the final stacking order before stacking the <type>s
stack_order_from_bottom_to_top = determine_final_stacking_order(objects_to_enforce_order=<type>_names_with_strick_order_from_bottom_to_top, objects_without_order=<type>_names_without_order)
stack_without_height_limit(objects_to_stack=stack_order_from_bottom_to_top)''',
            'fully-ordered': '''say("Stack all <type>s into one stack.")
say("There is 1 scenario: [Scenario 1].")
say("Based on [Scenario 1]'s states, listing the <type>s in the stack from bottom to top: <stack_1>")
say("Since there's only 1 scenario, we assume that the blocks must be stacked in the order above.")
# Because all the orders have been specified, stack all <type>s based on that order
stack_order_from_bottom_to_top = <stack_1>
stack_without_height_limit(objects_to_stack=stack_order_from_bottom_to_top)'''
        }
    },
    'stack-all-objects': {
        'num_objs': 0,
        'descriptions':{
            'none': "Stack all objects into two stacks (where each stack has maximum height of 4).",
            'none-specific': "Stack all objects into two stacks (where each stack has maximum height of 4). It doesn't matter whether the objects are categorized.",
            'categorized': "Stack all objects into two stacks (where each stack has maximum height of 4). Create one stack that only has blocks, and create another stack that only has cylinders."
        },
        'code_with-say':{
            'none': '''say("Stack all objects into two stacks (where each stack has maximum height of 4).")
say("It doesn't matter whether the objects are categorized.")
object_names = get_obj_names()
stack_1 = object_names[:4]
stack_2 = object_names[4:]
stack_without_height_limit(objects_to_stack=stack_1)
stack_without_height_limit(objects_to_stack=stack_2)'''
        },
        'code_with-say_cot':{
            'none': '''say("Stack all objects into two stacks (where each stack has maximum height of 4).")
say("Based on [Scenario 1]'s states, stack 1 (from bottom to top): []")
say("stack 1 contains both cylinders and blocks.")
say("Based on [Scenario 1]'s states, stack 2 (from bottom to top): []")
say("stack 2 contains both cylinders and blocks.")
say("Because the two stacks have both blocks and cylinders, we assume that it doesn't matter whether the objects are categorized.")
object_names = get_obj_names()
stack_1 = object_names[:4]
stack_2 = object_names[4:]
stack_without_height_limit(objects_to_stack=stack_1)
stack_without_height_limit(objects_to_stack=stack_2)'''
        }
    }
}

predicates_to_lang = {
    "on_top_of": "'<obj_1>' is <true>on top of '<obj_2>'",
    "is_at": "'<obj_1>' is <true>at '<obj_2>'",
    "is_left_of": "'<obj_1>' is <true>to the left of '<obj_2>'",
    "is_right_of": "'<obj_1>' is <true>to the right of '<obj_2>'",
    "is_behind": "'<obj_1>' is <true>behind '<obj_2>'",
    "is_in_front_of": "'<obj_1>' is <true>in front of '<obj_2>'",
    'has_moved': "'<obj_1>' has <true>moved"
}
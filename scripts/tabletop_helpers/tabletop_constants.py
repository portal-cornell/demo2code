import numpy as np

# Global constants: pick and place objects, colors, workspace bounds
COLORS = {
    'blue':   (78/255,  121/255, 167/255, 255/255),
    'red':    (255/255,  87/255,  89/255, 255/255),
    'green':  (89/255,  169/255,  79/255, 255/255),
    'orange': (242/255, 142/255,  43/255, 255/255),
    'yellow': (237/255, 201/255,  72/255, 255/255),
    'purple': (176/255, 122/255, 161/255, 255/255),
    'pink':   (255/255, 157/255, 167/255, 255/255),
    'cyan':   (118/255, 183/255, 178/255, 255/255),
    'brown':  (156/255, 117/255,  95/255, 255/255),
    'gray':   (186/255, 176/255, 172/255, 255/255),
}

CORNER_POS = {
  'top left corner':     (-0.3 + 0.05, -0.2 - 0.05, 0),
  'top edge':            (0,           -0.2 - 0.05, 0),
  'top right corner':    (0.3 - 0.05,  -0.2 - 0.05, 0),
  'left edge':           (-0.3 + 0.05, -0.5,        0),
  'middle':              (0,           -0.5,        0),
  'right edge':          (0.3 - 0.05,  -0.5,        0),
  'bottom left corner':  (-0.3 + 0.05, -0.8 + 0.05, 0),
  'bottom edge':         (0,           -0.8 + 0.05, 0),
  'bottom right corner': (0.3 - 0.05,  -0.8 + 0.05, 0),
}

lmp_tabletop_coords = {
        'top_left':     (-0.3 + 0.05, -0.2 - 0.05),
        'top_edge':     (0,           -0.2 - 0.05),
        'top_right':    (0.3 - 0.05,  -0.2 - 0.05),
        'left_edge':    (-0.3 + 0.05, -0.5,      ),
        'middle':       (0,           -0.5,      ),
        'right_edge':   (0.3 - 0.05,  -0.5,      ),
        'bottom_left':  (-0.3 + 0.05, -0.8 + 0.05),
        'bottom_edge':  (0,           -0.8 + 0.05),
        'bottom_right': (0.3 - 0.05,  -0.8 + 0.05),
        'table_z':       0.0,
      }

# for generating the blocks
ALL_BLOCKS = ['blue block', 'red block', 'green block', 'orange block', 'yellow block', 'purple block', 'pink block', 'cyan block', 'brown block', 'gray block']
ALL_CYLINDERS = ['blue cylinder', 'red cylinder', 'green cylinder', 'orange cylinder', 'yellow cylinder', 'purple cylinder', 'pink cylinder', 'cyan cylinder', 'brown cylinder', 'gray cylinder']

MAX_NUM_BLOCKS = 3
MAX_NUM_CYLINDERS = 3

ON_TABLE_MIN_DIST_BTW_OBJS = 0.125  # starting minimum distance between objects that ARE ON THE TABLE (this can decrease)
SMALLEST_ON_TABLE_MIN_DIST_BTW_OBJS = 0.105  # the smallest possible minimum distance between objects that ARE ON THE TABLE

MIN_DIST_BTW_OBJS = 0.16  # starting minimum distance between objects (this can decrease)
SMALLEST_MIN_DIST_BTW_OBJS = 0.11  # the smallest possible minimum distance between objects

MIN_DIST_BTW_OBJS_DECREMENT_AMT = 0.01  # the amount to decrease in order to randomly generate a valid tabletop initial configuration

PIXEL_SIZE = 0.00267857
BOUNDS = np.float32([[-0.3, 0.3], [-0.8, -0.2], [0, 0.15]])  # X Y Z

# for predicates
NEXT_TO_DIST = 0.15
XY_NEXT_TO_TOL_DIST = 0.04
Z_NEXT_TO_TOL_DIST = 0.01
Z_ON_TABLE_TOL_DIST = 0.025
NOT_MOVED_TOL_DIST = 0.01
NOT_MOVED_TOL_DIST_Z = 0.02

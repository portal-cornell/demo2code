import numpy as np
from shapely.geometry import *
from shapely.affinity import *
from scripts.tabletop_helpers.tabletop_constants import *
from scripts.overall_helpers.utils import *

class LMP_wrapper():

    def __init__(self, env, cfg, randomize, render=False):
        self.env = env
        self._cfg = cfg
        self.object_names = list(self._cfg['env']['init_objs'])

        self._min_xy = np.array(self._cfg['env']['coords']['bottom_left'])
        self._max_xy = np.array(self._cfg['env']['coords']['top_right'])
        self._range_xy = self._max_xy - self._min_xy

        self._table_z = self._cfg['env']['coords']['table_z']

        self.randomize = randomize
        self.render = render

    def is_obj_visible(self, obj_name):
        return obj_name in self.object_names

    def get_obj_names(self):
        obj_names = self.object_names[::]
        if self.randomize: 
            np.random.shuffle(obj_names)
        return obj_names

    def denormalize_xy(self, pos_normalized):
        return pos_normalized * self._range_xy + self._min_xy

    def get_corner_positions(self):
        unit_square = box(0, 0, 1, 1)
        normalized_corners = np.array(list(unit_square.exterior.coords))[:4]
        corners = np.array(([self.denormalize_xy(corner) for corner in normalized_corners]))
        return corners

    def get_edge_positions(self):
        edge_xs = np.array([0, 0.5, 0.5, 1])
        edge_ys = np.array([0.5, 0, 1, 0.5])
        normalized_edge_positions = np.c_[edge_xs, edge_ys]
        edge_positions = np.array(([self.denormalize_xy(corner) for corner in normalized_edge_positions]))
        return edge_positions

    def get_obj_pos(self, obj_name):
        # return the xyz position of the object in robot base frame
        return self.env.get_obj_pos(obj_name)

    def get_obj_xy_pos(self, obj_name):
        # return the xy position of the object in robot base frame
        return self.env.get_obj_pos(obj_name)[:2]

    def get_obj_position_np(self, obj_name):
        return self.get_pos(obj_name)

    def get_bbox(self, obj_name):
        # return the axis-aligned object bounding box in robot base frame (not in pixels)
        # the format is (min_x, min_y, max_x, max_y)
        bbox = self.env.get_bounding_box(obj_name)
        return bbox

    def get_color(self, obj_name):
        for color, rgb in COLORS.items():
            if color in obj_name:
                return rgb

    def pick_place(self, pick_pos, place_pos):
        pick_pos_xyz = np.r_[pick_pos, [self._table_z]]
        place_pos_xyz = np.r_[place_pos, [self._table_z]]
        pass

    def put_first_on_second(self, arg1, arg2):
        # put the object with obj_name on top of target
        # target can either be another object name, or it can be an x-y position in robot base frame
        pick_pos = self.get_obj_pos(arg1) if isinstance(arg1, str) else arg1
        place_pos = self.get_obj_pos(arg2) if isinstance(arg2, str) else arg2
        self.env.step(action={'pick': pick_pos, 'place': place_pos})

    def get_robot_pos(self):
        # return robot end-effector xy position in robot base frame
        return self.env.get_ee_pos()

    def goto_pos(self, position_xy):
        # move the robot end-effector to the desired xy position while maintaining same z
        ee_xyz = self.env.get_ee_pos()
        position_xyz = np.concatenate([position_xy, ee_xyz[-1]])
        while np.linalg.norm(position_xyz - ee_xyz) > 0.01:
            self.env.movep(position_xyz)
            self.env.step_sim_and_render()
            ee_xyz = self.env.get_ee_pos()

    def follow_traj(self, traj):
        for pos in traj:
            self.goto_pos(pos)

    def get_corner_positions(self):
        normalized_corners = np.array([
            [0, 1],
            [1, 1],
            [0, 0],
            [1, 0]
        ])
        return np.array(([self.denormalize_xy(corner) for corner in normalized_corners]))

    def get_edge_positions(self):
        normalized_edges = np.array([
            [0.5, 1],
            [1, 0.5],
            [0.5, 0],
            [0, 0.5]
        ])
        return np.array(([self.denormalize_xy(edge) for edge in normalized_edges]))

    def get_corner_name(self, pos):
        corner_positions = self.get_corner_positions()
        corner_idx = np.argmin(np.linalg.norm(corner_positions - pos, axis=1))
        return ['top left corner', 'top right corner', 'bottom left corner', 'botom right corner'][corner_idx]

    def get_edge_name(self, pos):
        edge_positions = self.get_edge_positions()
        edge_idx = np.argmin(np.linalg.norm(edge_positions - pos, axis=1))
        return ['top edge', 'right edge', 'bottom edge', 'left edge'][edge_idx]

    def get_all_obj_names_that_match_type(self, type_name, objects_list):
        type_name_processed = type_name.replace('the', '').replace('_', ' ').strip()
        if type_name_processed[-1] == "s":
            type_name_processed = type_name_processed[:-1]

        if type_name_processed != "block" and type_name_processed != "cylinder":
            raise ExecError

        return [obj for obj in objects_list if type_name_processed in obj]

    def stack_without_height_limit(self, objects_to_stack):
        # so that it will also move the first object
        self.put_first_on_second(objects_to_stack[0], "table")

        for i in range(1, len(objects_to_stack)):
            self.put_first_on_second(objects_to_stack[i], objects_to_stack[i-1])

    def stack_with_height_limit(self, objects_to_stack, height_limit):
        stack_height = 0
        for i in range(len(objects_to_stack)):
            if stack_height == 0:
                # this is the bottom of the new stack, so no need to stack anything
                #   but we do move the object to the table
                stack_height += 1
                self.put_first_on_second(objects_to_stack[i], "table")
            elif stack_height > 0 and stack_height < height_limit:
                self.put_first_on_second(objects_to_stack[i], objects_to_stack[i-1])
                stack_height += 1

                if stack_height == height_limit:
                    # start a new stack
                    stack_height = 0


    def flatten_list(self, _2d_list):
        flat_list = []
        # Iterate through the outer list
        for element in _2d_list:
            if type(element) is list:
                # If the element is of type list, iterate through the sublist
                for item in element:
                    flat_list.append(item)
            else:
                flat_list.append(element)
        return flat_list


    def determine_final_stacking_order(self, objects_to_enforce_order, objects_without_order):
        stack_order = ["objects_with_order"] + objects_without_order
        np.random.shuffle(stack_order)
        stack_order = [obj if obj != "objects_with_order" else objects_to_enforce_order for obj in stack_order]
        return self.flatten_list(stack_order)

import time
import numpy as np
import re

from scripts.overall_helpers.utils import MaxStepsError

ROBOTOUILLE_MAX_STEPS = 100

def print_states(obs):
    states = obs.literals
    for state in states:
        print(f"- {state}")
        
class RobotouilleAPI():
    def __init__(self, env, env_json, state_save_path, render):
        self.env = env

        self.sleep_time = 0.1

        self.render = render

        self._state_save_path = state_save_path

        self._state_counter = 1

        self.initial_true_states = None
        self.predicate_vec_meaning = None
        self.init_predicate_vec = None
        self.curr_predicate_vec = None
        self.predicates_to_include = None

        self._curr_loc = ""

        self.predicates_to_not_repr = ["vacant", "nothing", "empty", "clear", "on(.)*:station\)"]

        self.env_json = env_json

    def reset(self):
        """
        Reset the Robotouille environment (so all the state predicates are initialized)
        """
        obs, info = self.env.reset()
        
        self.initial_true_states = []
        for x in obs.literals:
            self.initial_true_states.append(str(x))

        with open(self._state_save_path, "w") as fout:
            fout.write("")

        robot_at_re = re.compile(r"loc\(robot1:player,(.*):station\)")
        robot_at_re_match_list = list(filter(robot_at_re.match, self.initial_true_states))
        robot_loc_list = [robot_at_re.search(s).group(1) for s in robot_at_re_match_list]

        if len(robot_loc_list) == 1:
            self._curr_loc = robot_loc_list[0]
        else:
            print(robot_loc_list)
            print(self.initial_true_states)
            print("found multiple location that the robot is at")
            assert False

        if self.render:
            self.env.render(mode='human')

    def _repr_predicates_given_index(self, predicates_str_rep_list, predicates_value_list, idx_to_include):
        ret_str = ""

        if type(idx_to_include) == np.ndarray or type(idx_to_include) == list:
            for i in range(len(idx_to_include)):
                if idx_to_include[i]:
                    predicates_name = str(predicates_str_rep_list[i])

                    skip = False
                    for keyword in self.predicates_to_not_repr:
                        if not skip:
                            if re.search(keyword, predicates_name):
                                skip = True
                    
                    if not skip:
                        ret_str += f"{predicates_str_rep_list[i]}:{int(predicates_value_list[i])}\n"

        return ret_str
    

    def _get_curr_predicates_value_list(self, predicates_value_list, idx_to_include):
        new_predicates_value_list = []
        for i in range(len(idx_to_include)):
            if idx_to_include[i]:
                # toggle the value
                predicate_value = int(np.abs(1 - int(predicates_value_list[i])))
                new_predicates_value_list.append(predicate_value)
            else:
                new_predicates_value_list.append(predicates_value_list[i])
            
        return np.array(new_predicates_value_list)
    

    def log_init_predicates(self):
        predicates_str = self._repr_predicates_given_index(self.predicate_vec_meaning, self.init_predicate_vec, self.predicates_to_include)
        with open(self._state_save_path, "a") as fout:
            fout.write("<init-state>\n")
            fout.write(predicates_str)


    def _action_wrapper(self, action_str):
        if self._state_counter > ROBOTOUILLE_MAX_STEPS:
            raise MaxStepsError
        
        self._state_counter += 1

        if self.sleep_time != 0:
            time.sleep(self.sleep_time) 

        print(f"{self._state_counter}: {action_str}")
        _, _, _, info = self.env.step(action_str)

        # store the initial state
        if self._state_counter == 2:
            # "expanded_truths" is the truth of the previous timestep
            self.predicate_vec_meaning = info['expanded_states']
            self.predicate_vec_meaning = [str(p) for p in self.predicate_vec_meaning]
            
            self.init_predicate_vec = info['expanded_truths']
            self.predicates_to_include = np.zeros(len(self.init_predicate_vec))

        # self.predicate_vec_meaning = info['expanded_states']
        self.curr_predicate_vec = self._get_curr_predicates_value_list(info['expanded_truths'], 
                                                                            info['toggle_array'])
        self.predicates_to_include = np.abs(self.predicates_to_include - info["toggle_array"])
        predicates_str = self._repr_predicates_given_index(info['expanded_states'],
                                                        self.curr_predicate_vec, 
                                                        info['toggle_array'])
        print(predicates_str)
        if predicates_str == "":
            predicates_str += "\n"
            
        with open(self._state_save_path, "a") as fout:
            fout.write(f"<state-{self._state_counter}>\n")
            fout.write(f"{predicates_str}\n")

        if self.render:
            self.env.render(mode='human')


    def move(self, start_loc, end_loc):
        if "cutting_board" in end_loc:
            _, _, board_id = end_loc.partition("board")
            end_loc = f"board{board_id}"
        action_str = f"move(robot1:player,{start_loc}:station,{end_loc}:station)"
        self._action_wrapper(action_str)
        self._curr_loc = end_loc

    def basic_move(self, target_loc):
        curr_loc = self.get_curr_location()
        if curr_loc != target_loc:
            self.move(curr_loc, target_loc)

    def get_curr_location(self):
        return self._curr_loc
    
    def get_obj_location(self, obj_name):
        at_re = re.compile(f"at\({obj_name}([0-9]*):item,(.*):station\)")

        if type(self.predicate_vec_meaning) == list:
            predicate_vec_meaning = self.predicate_vec_meaning
        else:
            # use the initial data
            predicate_vec_meaning = self.initial_true_states

        at_match_list = list(filter(at_re.match, predicate_vec_meaning))

        if type(self.predicate_vec_meaning) == list:
            at_match_list_index = [self.predicate_vec_meaning.index(s) for s in at_match_list]

            for i in at_match_list_index:
                if self.curr_predicate_vec[i] == 1:
                    return at_re.search(self.predicate_vec_meaning[i]).group(2)
                
            # input(f"WARNING: unable to find the location of item: {obj_name}")
        else:
            # using the initial data (there has to be only 1 possible location)
            if len(at_match_list) == 1:
                # print([at_re.search(s).group(2) for s in at_match_list])
                # input("sotp")
                return [at_re.search(s).group(2) for s in at_match_list][0]
            elif len(at_match_list) == 0:
                return ""
            else:
                print("using initial state but found multiple location when the object is there")
                print(predicate_vec_meaning)
                print(at_match_list)
                input("stop")
        
        return "location"

    def pick(self, item, loc):
        self.pick_up(item, loc)

    def pick_up(self, item, loc):
        action_str = f"pick-up(robot1:player,{item}:item,{loc}:station)"
        self._action_wrapper(action_str)

    def place(self, item, loc):
        action_str = f"place(robot1:player,{item}:item,{loc}:station)"
        self._action_wrapper(action_str)

    def cut(self, item):
        action_str = f"cut(robot1:player,{item}:item,{self._curr_loc}:station)"
        self._action_wrapper(action_str)

    def start_cooking(self, item):
        # def cook(self, item, loc):
        action_str = f"cook(robot1:player,{item}:item,{self._curr_loc}:station)"
        self._action_wrapper(action_str)

    def stack(self, item_to_stack, item_at_bottom):
        action_str = f"stack(robot1:player,{item_to_stack}:item,{item_at_bottom}:item,{self._curr_loc}:station)"
        self._action_wrapper(action_str)

    def unstack(self, item_to_unstack, item_to_unstack_from):
        action_str = f"unstack(robot1:player,{item_to_unstack}:item,{item_to_unstack_from}:item,{self._curr_loc}:station)"
        self._action_wrapper(action_str)

    def noop(self):
        self._action_wrapper("noop")

    def is_cut(self, item):
        cuttable_str = f"iscuttable({item}:item)"
        iscut_str = f"iscut({item}:item)"
        # TODO: This is a hack since predicate_vec_meaning isn't set until the first step
        try:
            cuttable_str_idx = self.predicate_vec_meaning.index(cuttable_str)
            iscut_str_idx = self.predicate_vec_meaning.index(iscut_str)
        except:
            return False
        

        return bool(self.curr_predicate_vec[cuttable_str_idx]) and bool(self.curr_predicate_vec[iscut_str_idx])

    def is_cooked(self, item):
        cookable_str = f"iscookable({item}:item)"
        iscooked_str = f"iscooked({item}:item)"

        if type(self.predicate_vec_meaning) == list:
            cookable_str_idx = self.predicate_vec_meaning.index(cookable_str)
            iscooked_str_idx = self.predicate_vec_meaning.index(iscooked_str)

            return bool(self.curr_predicate_vec[cookable_str_idx]) and bool(self.curr_predicate_vec[iscooked_str_idx])
        return (cookable_str in self.initial_true_states) and (iscooked_str in self.initial_true_states)
    
    def is_holding(self, item):
        re_compile = re.compile(f"has\(robot1:player,{item}([0-9]*):item\)")

        if type(self.predicate_vec_meaning) == list:
            predicate_vec_meaning = self.predicate_vec_meaning
        else:
            # use the initial data
            predicate_vec_meaning = self.initial_true_states

        at_match_list = list(filter(re_compile.match, predicate_vec_meaning))
        
        if type(self.predicate_vec_meaning) == list:
            str_idx = self.predicate_vec_meaning.index(f"has(robot1:player,{item}:item)")
            return bool(self.curr_predicate_vec[str_idx])
        else:
            # use the initial data
            return len(at_match_list) == 1

    def is_in_a_stack(self, item):
        re_compile = re.compile(f"atop\({item}:item,(.*):item\)")

        if type(self.predicate_vec_meaning) == list:
            predicate_vec_meaning = self.predicate_vec_meaning
        else:
            # use the initial data
            predicate_vec_meaning = self.initial_true_states

        at_match_list = list(filter(re_compile.match, predicate_vec_meaning))

        if type(self.predicate_vec_meaning) == list:
            at_match_list_index = [self.predicate_vec_meaning.index(s) for s in at_match_list]

            for i in at_match_list_index:
                if self.curr_predicate_vec[i] == 1:
                    return True
            return False
        else:
            # use the initial data
            return len(at_match_list) == 1
    
    def get_obj_that_is_underneath(self, obj_at_top):
        re_compile = re.compile(f"atop\({obj_at_top}:item,(.*):item\)")

        if type(self.predicate_vec_meaning) == list:
            predicate_vec_meaning = self.predicate_vec_meaning
        else:
            # use the initial data
            predicate_vec_meaning = self.initial_true_states

        at_match_list = list(filter(re_compile.match, predicate_vec_meaning))

        if type(self.predicate_vec_meaning) == list:
            at_match_list_index = [self.predicate_vec_meaning.index(s) for s in at_match_list]

            for i in at_match_list_index:
                if self.curr_predicate_vec[i] == 1:
                    return re_compile.search(self.predicate_vec_meaning[i]).group(1)
        else:
            # using the initial data (there has to be only 1 possible object)
            if len(at_match_list) == 1:
                return [re_compile.search(s).group(1) for s in at_match_list][0]
            elif len(at_match_list) == 0:
                return ""
            else:
                print("using initial state but found multiple location when the object is there")
                print(predicate_vec_meaning)
                print(at_match_list)
                assert False

    def get_all_objects(self):
        """
        Return:
            a list of all the objects in the environment
        """
        return [item['name'] for item in self.env_json['items']]
    
    def get_all_locations(self):
        """
        Return:
            a list of all the locations in the environment
        """
        return [item['name'] for item in self.env_json['stations']]

    def get_all_obj_names_that_match_type(self, obj_type):
        all_objects = self.get_all_objects()

        if "bun" in obj_type and "top" in obj_type:
            obj_type_to_search = "topbun"
        elif "bun" in obj_type and "bottom" in obj_type:
            obj_type_to_search = "bottombun"
        else:
            obj_type_to_search = obj_type

        relevant_obj_names = [obj for obj in all_objects if obj_type_to_search in obj]

        return relevant_obj_names
    
    def get_all_location_names_that_match_type(self, location_type):
        all_locations = self.get_all_locations()

        if "board" in location_type:
            location_type_to_search = "board"
        else:
            location_type_to_search = location_type

        relevant_location_names = [loc for loc in all_locations if location_type_to_search in loc]
        if location_type_to_search in ['stove', 'board', 'table']:
            # Ensure these locations are empty (no objects on them)
            filled_stations = [self.get_obj_location(obj) for obj in self.get_all_objects()]
            relevant_location_names = list(filter(lambda station: station not in filled_stations, relevant_location_names))
        
        return relevant_location_names
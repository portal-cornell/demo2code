import os
import numpy as np
import pybullet
import pybullet_data
import threading
from time import sleep

# import global constants
from scripts.tabletop_helpers.tabletop_constants import *
from scripts.overall_helpers.utils import ExecError

# Gripper (Robotiq 2F85) code
class Robotiq2F85:
  """Gripper handling for Robotiq 2F85."""

  def __init__(self, robot, tool):
    self.robot = robot
    self.tool = tool
    pos = [0.1339999999999999, -0.49199999999872496, 0.5]
    rot = pybullet.getQuaternionFromEuler([np.pi, 0, np.pi])
    urdf = './data/tabletop/env_setup_data/robotiq_2f_85/robotiq_2f_85.urdf'
    self.body = pybullet.loadURDF(urdf, pos, rot)
    self.n_joints = pybullet.getNumJoints(self.body)
    self.activated = False

    # Connect gripper base to robot tool.
    pybullet.createConstraint(self.robot, tool, self.body, 0, jointType=pybullet.JOINT_FIXED, jointAxis=[0, 0, 0], parentFramePosition=[0, 0, 0], childFramePosition=[0, 0, -0.07], childFrameOrientation=pybullet.getQuaternionFromEuler([0, 0, np.pi / 2]))

    # Set friction coefficients for gripper fingers.
    for i in range(pybullet.getNumJoints(self.body)):
      pybullet.changeDynamics(self.body, i, lateralFriction=10.0, spinningFriction=1.0, rollingFriction=1.0, frictionAnchor=True)

    # Start thread to handle additional gripper constraints.
    self.motor_joint = 1
    self.constraints_thread = threading.Thread(target=self.step)
    self.constraints_thread.daemon = True
    self.constraints_thread.start()

  # Control joint positions by enforcing hard contraints on gripper behavior.
  # Set one joint as the open/close motor joint (other joints should mimic).
  def step(self):
    while True:
      try:
        currj = [pybullet.getJointState(self.body, i)[0] for i in range(self.n_joints)]
        indj = [6, 3, 8, 5, 10]
        targj = [currj[1], -currj[1], -currj[1], currj[1], currj[1]]
        pybullet.setJointMotorControlArray(self.body, indj, pybullet.POSITION_CONTROL, targj, positionGains=np.ones(5))
      except:
        return
      sleep(0.001)

  # Close gripper fingers.
  def activate(self):
    pybullet.setJointMotorControl2(self.body, self.motor_joint, pybullet.VELOCITY_CONTROL, targetVelocity=1, force=10)
    self.activated = True

  # Open gripper fingers.
  def release(self):
    pybullet.setJointMotorControl2(self.body, self.motor_joint, pybullet.VELOCITY_CONTROL, targetVelocity=-1, force=10)
    self.activated = False

  # If activated and object in gripper: check object contact.
  # If activated and nothing in gripper: check gripper contact.
  # If released: check proximity to surface (disabled).
  def detect_contact(self):
    obj, _, ray_frac = self.check_proximity()
    if self.activated:
      empty = self.grasp_width() < 0.01
      cbody = self.body if empty else obj
      if obj == self.body or obj == 0:
        return False
      return self.external_contact(cbody)
  #   else:
  #     return ray_frac < 0.14 or self.external_contact()

  # Return if body is in contact with something other than gripper
  def external_contact(self, body=None):
    if body is None:
      body = self.body
    pts = pybullet.getContactPoints(bodyA=body)
    pts = [pt for pt in pts if pt[2] != self.body]
    return len(pts) > 0  # pylint: disable=g-explicit-length-test

  def check_grasp(self):
    while self.moving():
      sleep(0.001)
    success = self.grasp_width() > 0.01
    return success

  def grasp_width(self):
    lpad = np.array(pybullet.getLinkState(self.body, 4)[0])
    rpad = np.array(pybullet.getLinkState(self.body, 9)[0])
    dist = np.linalg.norm(lpad - rpad) - 0.047813
    return dist

  def check_proximity(self):
    ee_pos = np.array(pybullet.getLinkState(self.robot, self.tool)[0])
    tool_pos = np.array(pybullet.getLinkState(self.body, 0)[0])
    vec = (tool_pos - ee_pos) / np.linalg.norm((tool_pos - ee_pos))
    ee_targ = ee_pos + vec
    ray_data = pybullet.rayTest(ee_pos, ee_targ)[0]
    obj, link, ray_frac = ray_data[0], ray_data[1], ray_data[2]
    return obj, link, ray_frac
  
# Gym-style environment code

class PickPlaceEnv():
  def __init__(self, state_save_path, on_table_min_dist_btw_objs, render=False, high_res=False, high_frame_rate=False):
    self.dt = 1/480
    self.sim_step = 0

    # Configure and start PyBullet.
    # python3 -m pybullet_utils.runServer
    # pybullet.connect(pybullet.SHARED_MEMORY)  # pybullet.GUI for local GUI.
    pybullet.connect(pybullet.DIRECT)  # pybullet.GUI for local GUI.
    pybullet.configureDebugVisualizer(pybullet.COV_ENABLE_GUI, 0)
    pybullet.setPhysicsEngineParameter(enableFileCaching=0)
    assets_path = os.path.dirname(os.path.abspath(""))
    pybullet.setAdditionalSearchPath(assets_path)
    pybullet.setAdditionalSearchPath(pybullet_data.getDataPath())
    pybullet.setTimeStep(self.dt)

    self.home_joints = (np.pi / 2, -np.pi / 2, np.pi / 2, -np.pi / 2, 3 * np.pi / 2, 0)  # Joint angles: (J0, J1, J2, J3, J4, J5).
    self.home_ee_euler = (np.pi, 0, np.pi)  # (RX, RY, RZ) rotation in Euler angles.
    self.ee_link_id = 9  # Link ID of UR5 end effector.
    self.tip_link_id = 10  # Link ID of gripper finger tips.
    self.gripper = None

    self.render = render
    self.high_res = high_res
    self.high_frame_rate = high_frame_rate

    self._on_table_min_dist_btw_objs = on_table_min_dist_btw_objs

    # predicates
    self.predicate_vec_meaning = []
    self.init_predicate_vec = None
    self.curr_predicate_vec = None
    self.predicates_to_include = None

    self.state_save_path = state_save_path


  def init_random_obj_postion(self, obj_xyz_old, min_dist=0.16):
    # Get random position 15cm+ from other objects.
    max_step = 10000
    step = 0

    obj_xyz = obj_xyz_old

    while True:
      rand_x = np.random.uniform(BOUNDS[0, 0] + 0.1, BOUNDS[0, 1] - 0.1)
      rand_y = np.random.uniform(BOUNDS[1, 0] + 0.1, BOUNDS[1, 1] - 0.1)
      rand_xyz = np.float32([rand_x, rand_y, 0.03]).reshape(1, 3)
      if len(obj_xyz) == 0:
        obj_xyz = np.concatenate((obj_xyz, rand_xyz), axis=0)
        break
      else:
        nn_dist = np.min(np.linalg.norm(obj_xyz - rand_xyz, axis=1)).squeeze()
        if nn_dist > min_dist:
          obj_xyz = np.concatenate((obj_xyz, rand_xyz), axis=0)
          break
      
      if step >= max_step:
        print("raise ExecError: unable to find a good placement location")
        raise ExecError
      
      step += 1

    object_position = rand_xyz.squeeze()

    return object_position, obj_xyz

    
  def create_obj_based_on_type(self, obj_name, object_position):
    object_color = COLORS[obj_name.split(' ')[0]]
    object_type = obj_name.split(' ')[1]

    if object_type == 'block':
      object_shape = pybullet.createCollisionShape(pybullet.GEOM_BOX, halfExtents=[0.02, 0.02, 0.02])
      object_visual = pybullet.createVisualShape(pybullet.GEOM_BOX, halfExtents=[0.02, 0.02, 0.02])
      object_id = pybullet.createMultiBody(0.01, object_shape, object_visual, basePosition=object_position)
    elif object_type == 'cylinder':
      # object_position[2] = 0  # this causes cylinder to not behave well
      object_shape = pybullet.createCollisionShape(pybullet.GEOM_CYLINDER, radius = 0.03, height = 0.04)
      object_visual = pybullet.createVisualShape(pybullet.GEOM_CYLINDER, radius = 0.03, length = 0.04)
      object_id = pybullet.createMultiBody(0.01, object_shape, object_visual, basePosition=object_position)
    
    pybullet.changeVisualShape(object_id, -1, rgbaColor=object_color)
    self.obj_name_to_id[obj_name] = object_id
    self.obj_init_pos[obj_name] = object_position


  def reset(self, object_list, init_obj_pos_list=[], obj_placement_dict={}, min_dist_btw_objs=0.16):
    pybullet.resetSimulation(pybullet.RESET_USE_DEFORMABLE_WORLD)
    pybullet.setGravity(0, 0, -9.8)
    self.cache_video = []

    # Temporarily disable rendering to load URDFs faster.
    pybullet.configureDebugVisualizer(pybullet.COV_ENABLE_RENDERING, 0)

    # Add robot.
    pybullet.loadURDF("plane.urdf", [0, 0, -0.001])
    self.robot_id = pybullet.loadURDF("./data/tabletop/env_setup_data/ur5e/ur5e.urdf", [0, 0, 0], flags=pybullet.URDF_USE_MATERIAL_COLORS_FROM_MTL)
    self.ghost_id = pybullet.loadURDF("./data/tabletop/env_setup_data/ur5e/ur5e.urdf", [0, 0, -10])  # For forward kinematics.
    self.joint_ids = [pybullet.getJointInfo(self.robot_id, i) for i in range(pybullet.getNumJoints(self.robot_id))]
    self.joint_ids = [j[0] for j in self.joint_ids if j[2] == pybullet.JOINT_REVOLUTE]

    # Move robot to home configuration.
    for i in range(len(self.joint_ids)):
      pybullet.resetJointState(self.robot_id, self.joint_ids[i], self.home_joints[i])

    # Add gripper.
    if self.gripper is not None:
      while self.gripper.constraints_thread.is_alive():
        self.constraints_thread_active = False
    self.gripper = Robotiq2F85(self.robot_id, self.ee_link_id)
    self.gripper.release()

    # Add workspace.
    plane_shape = pybullet.createCollisionShape(pybullet.GEOM_BOX, halfExtents=[0.3, 0.3, 0.001])
    plane_visual = pybullet.createVisualShape(pybullet.GEOM_BOX, halfExtents=[0.3, 0.3, 0.001])
    plane_id = pybullet.createMultiBody(0, plane_shape, plane_visual, basePosition=[0, -0.5, 0])
    pybullet.changeVisualShape(plane_id, -1, rgbaColor=[0.2, 0.2, 0.2, 1.0])

    # Load objects according to config.
    self.object_list = object_list
    self.obj_name_to_id = {}
    self.obj_init_pos = {}

    obj_already_added = []
    obj_pos_list = []

    self.obj_xyz = np.zeros((0, 3))

    # Load the exisiting object position
    if init_obj_pos_list != []:
      j = 0

      if obj_placement_dict != {}:
        for base_obj_name in obj_placement_dict:
          if ('block' in base_obj_name) or ('cylinder' in base_obj_name):
            obj_already_added.append(base_obj_name)

            object_position = init_obj_pos_list[j]
            self.obj_xyz = np.concatenate((self.obj_xyz, np.expand_dims(object_position, axis=0)), axis=0)

            self.create_obj_based_on_type(base_obj_name, object_position=object_position)

            j += 1

            for stack_obj_name in obj_placement_dict[base_obj_name]:
              if ('block' in stack_obj_name) or ('cylinder' in stack_obj_name):
                obj_already_added.append(stack_obj_name)

                object_position = init_obj_pos_list[j]
                self.obj_xyz = np.concatenate((self.obj_xyz, np.expand_dims(object_position, axis=0)), axis=0)

                self.create_obj_based_on_type(stack_obj_name, object_position=object_position)

                j += 1
                
      for obj_name in object_list:
        if obj_already_added != []:
          if obj_name in obj_already_added:
            continue

        if ('block' in obj_name) or ('cylinder' in obj_name):
          object_position = init_obj_pos_list[j]
          self.obj_xyz = np.concatenate((self.obj_xyz, np.expand_dims(object_position, axis=0)), axis=0)

          self.create_obj_based_on_type(obj_name, object_position=object_position)

          j += 1
    else:
      # Need to generate the object position

      # start by priortizing the objects that should be at the bottom
      if obj_placement_dict != {}:
        for base_obj_name in obj_placement_dict:
          if ('block' in base_obj_name) or ('cylinder' in base_obj_name):
            # object_color, object_type = self.get_obj_color_and_type(base_obj_name)
            obj_already_added.append(base_obj_name)

            base_object_position, self.obj_xyz = self.init_random_obj_postion(obj_xyz_old=self.obj_xyz, min_dist=min_dist_btw_objs)
            obj_pos_list.append(base_object_position)

            self.create_obj_based_on_type(base_obj_name, object_position=base_object_position)

            z = 0.03 + 0.05

            for stack_obj_name in obj_placement_dict[base_obj_name]:
              if ('block' in stack_obj_name) or ('cylinder' in stack_obj_name):
                obj_already_added.append(stack_obj_name)

                # use the x and y of the base object (aka the object at the bottom)
                stack_obj_postion = base_object_position.copy()
                stack_obj_postion[2] = z
                obj_pos_list.append(stack_obj_postion)

                self.create_obj_based_on_type(stack_obj_name, object_position=stack_obj_postion)

                # increase the height for the next stack object
                z += 0.05

      for obj_name in object_list:

        if obj_already_added != []:
          if obj_name in obj_already_added:
            continue

        if ('block' in obj_name) or ('cylinder' in obj_name):
          object_position, self.obj_xyz = self.init_random_obj_postion(obj_xyz_old=self.obj_xyz, min_dist=min_dist_btw_objs)
          obj_pos_list.append(object_position)

          self.create_obj_based_on_type(obj_name, object_position=object_position)

    # Re-enable rendering.
    pybullet.configureDebugVisualizer(pybullet.COV_ENABLE_RENDERING, 1)

    for _ in range(200):
      pybullet.stepSimulation()

    # record object positions at reset
    self.init_pos = {name: self.get_obj_pos(name) for name in object_list}

    self.generate_predicate_vec_meaning()
    self.init_predicate_vec = self.generate_predicate_vec()
    self.curr_predicate_vec = self.init_predicate_vec

    self.predicates_to_include = np.zeros(len(self.init_predicate_vec))

    # intialize the file to save the states
    with open(self.state_save_path, "w") as fout:
      fout.write("")

    self.state_num = 1

    return self.get_observation(), obj_pos_list

  def servoj(self, joints):
    """Move to target joint positions with position control."""
    pybullet.setJointMotorControlArray(
      bodyIndex=self.robot_id,
      jointIndices=self.joint_ids,
      controlMode=pybullet.POSITION_CONTROL,
      targetPositions=joints,
      positionGains=[0.01]*6)
  
  def movep(self, position):
    """Move to target end effector position."""
    joints = pybullet.calculateInverseKinematics(
        bodyUniqueId=self.robot_id,
        endEffectorLinkIndex=self.tip_link_id,
        targetPosition=position,
        targetOrientation=pybullet.getQuaternionFromEuler(self.home_ee_euler),
        maxNumIterations=100)
    self.servoj(joints)

  def get_ee_pos(self):
    ee_xyz = np.float32(pybullet.getLinkState(self.robot_id, self.tip_link_id)[0])
    return ee_xyz

  # @profile
  def step(self, action=None):
    """Do pick and place motion primitive."""
    pick_pos, place_pos = action['pick'].copy(), action['place'].copy()

    max_step = 5000
    step = 0

    # Set fixed primitive z-heights.
    # Verified that changing to 0.25 is ok
    #     motivation for changing is bc with 3 objects the highest is 0.18 without considering
    #     the 3rd object's height. 0.2 might collide into something
    hover_xyz = np.float32([pick_pos[0], pick_pos[1], 0.25])

    if pick_pos.shape[-1] == 2:
      pick_xyz = np.append(pick_pos, 0.025)
    else:
      pick_xyz = pick_pos

    if place_pos.shape[-1] == 2:
      place_xyz = np.append(place_pos, 0.15)
    else:
      place_xyz = place_pos
      place_xyz[2] += 0.15  # add a litle offset, so hopefully no collision with base object

    # Move to object.
    ee_xyz = self.get_ee_pos()
    while np.linalg.norm(hover_xyz - ee_xyz) > 0.01 and step < max_step:
      self.movep(hover_xyz)
      self.step_sim_and_render()
      ee_xyz = self.get_ee_pos()

      step += 1

    if step >= max_step:
      raise ExecError
    step = 0

    while np.linalg.norm(pick_xyz - ee_xyz) > 0.01 and step < max_step:
      self.movep(pick_xyz)
      self.step_sim_and_render()
      ee_xyz = self.get_ee_pos()

      step += 1

    if step >= max_step:
      raise ExecError
    step = 0

    # Pick up object.
    self.gripper.activate()
    for _ in range(240):
      self.step_sim_and_render()
    while np.linalg.norm(hover_xyz - ee_xyz) > 0.01 and step < max_step:
      self.movep(hover_xyz)
      self.step_sim_and_render()
      ee_xyz = self.get_ee_pos()

      step += 1

    if step >= max_step:
      raise ExecError
    step = 0
    
    for _ in range(50):
      self.step_sim_and_render()
    
    # Move to place location.
    while np.linalg.norm(place_xyz - ee_xyz) > 0.01 and step < max_step:
      self.movep(place_xyz)
      self.step_sim_and_render()
      ee_xyz = self.get_ee_pos()

      step += 1

    if step >= max_step:
      raise ExecError
    step = 0

    # Place down object.
    while (not self.gripper.detect_contact()) and (place_xyz[2] > 0.03) and step < max_step:
      place_xyz[2] -= 0.001
      self.movep(place_xyz)
      for _ in range(3):
        self.step_sim_and_render()

      step += 1

    if step >= max_step:
      raise ExecError
    step = 0
      
    self.gripper.release()
    for _ in range(240):
      self.step_sim_and_render()
    place_xyz[2] = 0.2
    ee_xyz = self.get_ee_pos()
    while np.linalg.norm(place_xyz - ee_xyz) > 0.01 and step < max_step:
      self.movep(place_xyz)
      self.step_sim_and_render()
      ee_xyz = self.get_ee_pos()

      step += 1

    if step >= max_step:
      raise ExecError
    step = 0

    place_xyz = np.float32([0, -0.5, 0.2])
    while np.linalg.norm(place_xyz - ee_xyz) > 0.01 and step < max_step:
      self.movep(place_xyz)
      self.step_sim_and_render()
      ee_xyz = self.get_ee_pos()

      step += 1

    if step >= max_step:
      raise ExecError
    step = 0

    self.state_num += 1

    observation = self.get_observation()
    reward = self.get_reward()
    done = False
    info = {}

    return observation, reward, done, info

  def set_alpha_transparency(self, alpha: float) -> None:
    for id in range(20):
      visual_shape_data = pybullet.getVisualShapeData(id)
      for i in range(len(visual_shape_data)):
        object_id, link_index, _, _, _, _, _, rgba_color = visual_shape_data[i]
        rgba_color = list(rgba_color[0:3]) +  [alpha]
        pybullet.changeVisualShape(
            self.robot_id, linkIndex=i, rgbaColor=rgba_color)      
        pybullet.changeVisualShape(
            self.gripper.body, linkIndex=i, rgbaColor=rgba_color)

  def step_sim_and_render(self):
    pybullet.stepSimulation()
    self.sim_step += 1

    interval = 40 if self.high_frame_rate else 60
    # Render current image at 8 FPS.
    if self.sim_step % interval == 0 and self.render:
      self.cache_video.append(self.get_camera_image())

  def get_camera_image(self):
    if not self.high_res:
      image_size = (240, 240)
      intrinsics = (120., 0, 120., 0, 120., 120., 0, 0, 1)
    else:
      image_size=(360, 360)
      intrinsics=(180., 0, 180., 0, 180., 180., 0, 0, 1)
    color, _, _, _, _ = self.render_image(image_size, intrinsics)
    return color

  def get_reward(self):
    return None

  def get_observation(self):
    observation = {}

    # Render current image.
    if self.render:
      color, depth, position, orientation, intrinsics = self.render_image()

      # Get heightmaps and colormaps.
      points = self.get_pointcloud(depth, intrinsics)
      position = np.float32(position).reshape(3, 1)
      rotation = pybullet.getMatrixFromQuaternion(orientation)
      rotation = np.float32(rotation).reshape(3, 3)
      transform = np.eye(4)
      transform[:3, :] = np.hstack((rotation, position))
      points = self.transform_pointcloud(points, transform)
      heightmap, colormap, xyzmap = self.get_heightmap(points, color, BOUNDS, PIXEL_SIZE)

      observation["image"] = colormap
      observation["xyzmap"] = xyzmap
    
    observation["all_predicates"] = self.generate_predicate_vec()

    # get the idx of what predicates have changed
    observation["idx_of_changed_predicates"] = np.abs(self.curr_predicate_vec - observation["all_predicates"])
    
    self.curr_predicate_vec = observation["all_predicates"]
    self.predicates_to_include = np.abs(self.predicates_to_include - observation["idx_of_changed_predicates"])

    predicates_str = self.repr_relavant_predicates(observation["all_predicates"], observation["idx_of_changed_predicates"])
    
    if predicates_str != "":
      print(predicates_str)

      with open(self.state_save_path, "a") as fout:
        fout.write(f"<state-{self.state_num}>\n")
        fout.write(f"{predicates_str}\n")

    return observation
  
  def generate_predicate_vec_meaning(self):
    self.predicate_vec_meaning = []

    for obj in self.object_list:
      self.predicate_vec_meaning.append(f"on_top_of:{obj},table")
      self.predicate_vec_meaning.append(f"has_moved:{obj}")
      for loc in CORNER_POS.keys():
        if loc != "middle":
          self.predicate_vec_meaning.append(f"is_at:{obj},{loc}")
      for obj_b in self.object_list:
        if obj != obj_b:
            self.predicate_vec_meaning.append(f"is_left_of:{obj},{obj_b}")
            self.predicate_vec_meaning.append(f"is_right_of:{obj},{obj_b}")
            self.predicate_vec_meaning.append(f"is_behind:{obj},{obj_b}")
            self.predicate_vec_meaning.append(f"is_in_front_of:{obj},{obj_b}")
            self.predicate_vec_meaning.append(f"on_top_of:{obj},{obj_b}")

  def generate_predicate_vec(self):
    predicate_vec = []
    
    for obj in self.object_list:
      predicate_vec.append(int(self.on_top_of(obj, "table")))
      predicate_vec.append(int(self.has_changed_initial_pos(obj)))
      for loc in CORNER_POS.keys():
        if loc != "middle":
          predicate_vec.append(int(self.is_at(obj, loc)))
      for obj_b in self.object_list:
          if obj != obj_b:
              predicate_vec.append(int(self.is_left_of(obj, obj_b)))
              predicate_vec.append(int(self.is_right_of(obj, obj_b)))
              predicate_vec.append(int(self.is_behind(obj, obj_b)))
              predicate_vec.append(int(self.is_in_front_of(obj, obj_b)))
              predicate_vec.append(int(self.on_top_of(obj, obj_b)))

    return np.array(predicate_vec)
  
  def repr_relavant_predicates(self, predicates_vec, idx_to_include):
    ret_str = ""
    for i in range(len(idx_to_include)):
      if idx_to_include[i]:
        ret_str += f"{self.predicate_vec_meaning[i]}:{int(predicates_vec[i])}\n"

    return ret_str
  
  def log_init_predicates(self):
    predicates_str = self.repr_relavant_predicates(self.init_predicate_vec, self.predicates_to_include)
    with open(self.state_save_path, "a") as fout:
      fout.write("<init-state>\n")
      fout.write(predicates_str)

  def render_image(self, image_size=(720, 720), intrinsics=(360., 0, 360., 0, 360., 360., 0, 0, 1)):

    # Camera parameters.
    position = (0, -0.85, 0.4)
    orientation = (np.pi / 4 + np.pi / 48, np.pi, np.pi)
    orientation = pybullet.getQuaternionFromEuler(orientation)
    zrange = (0.01, 10.)
    noise=True

    # OpenGL camera settings.
    lookdir = np.float32([0, 0, 1]).reshape(3, 1)
    updir = np.float32([0, -1, 0]).reshape(3, 1)
    rotation = pybullet.getMatrixFromQuaternion(orientation)
    rotm = np.float32(rotation).reshape(3, 3)
    lookdir = (rotm @ lookdir).reshape(-1)
    updir = (rotm @ updir).reshape(-1)
    lookat = position + lookdir
    focal_len = intrinsics[0]
    znear, zfar = (0.01, 10.)
    viewm = pybullet.computeViewMatrix(position, lookat, updir)
    fovh = (image_size[0] / 2) / focal_len
    fovh = 180 * np.arctan(fovh) * 2 / np.pi

    # Notes: 1) FOV is vertical FOV 2) aspect must be float
    aspect_ratio = image_size[1] / image_size[0]
    projm = pybullet.computeProjectionMatrixFOV(fovh, aspect_ratio, znear, zfar)

    # Render with OpenGL camera settings.
    _, _, color, depth, segm = pybullet.getCameraImage(
        width=image_size[1],
        height=image_size[0],
        viewMatrix=viewm,
        projectionMatrix=projm,
        shadow=1,
        flags=pybullet.ER_SEGMENTATION_MASK_OBJECT_AND_LINKINDEX,
        renderer=pybullet.ER_BULLET_HARDWARE_OPENGL)

    # Get color image.
    color_image_size = (image_size[0], image_size[1], 4)
    color = np.array(color, dtype=np.uint8).reshape(color_image_size)
    color = color[:, :, :3]  # remove alpha channel
    if noise:
      color = np.int32(color)
      color += np.int32(np.random.normal(0, 3, color.shape))
      color = np.uint8(np.clip(color, 0, 255))

    # Get depth image.
    depth_image_size = (image_size[0], image_size[1])
    zbuffer = np.float32(depth).reshape(depth_image_size)
    depth = (zfar + znear - (2 * zbuffer - 1) * (zfar - znear))
    depth = (2 * znear * zfar) / depth
    if noise:
      depth += np.random.normal(0, 0.003, depth.shape)

    intrinsics = np.float32(intrinsics).reshape(3, 3)
    return color, depth, position, orientation, intrinsics

  def get_pointcloud(self, depth, intrinsics):
    """Get 3D pointcloud from perspective depth image.
    Args:
      depth: HxW float array of perspective depth in meters.
      intrinsics: 3x3 float array of camera intrinsics matrix.
    Returns:
      points: HxWx3 float array of 3D points in camera coordinates.
    """
    height, width = depth.shape
    xlin = np.linspace(0, width - 1, width)
    ylin = np.linspace(0, height - 1, height)
    px, py = np.meshgrid(xlin, ylin)
    px = (px - intrinsics[0, 2]) * (depth / intrinsics[0, 0])
    py = (py - intrinsics[1, 2]) * (depth / intrinsics[1, 1])
    points = np.float32([px, py, depth]).transpose(1, 2, 0)
    return points

  def transform_pointcloud(self, points, transform):
    """Apply rigid transformation to 3D pointcloud.
    Args:
      points: HxWx3 float array of 3D points in camera coordinates.
      transform: 4x4 float array representing a rigid transformation matrix.
    Returns:
      points: HxWx3 float array of transformed 3D points.
    """
    padding = ((0, 0), (0, 0), (0, 1))
    homogen_points = np.pad(points.copy(), padding,
                            'constant', constant_values=1)
    for i in range(3):
      points[Ellipsis, i] = np.sum(transform[i, :] * homogen_points, axis=-1)
    return points

  def get_heightmap(self, points, colors, bounds, pixel_size):
    """Get top-down (z-axis) orthographic heightmap image from 3D pointcloud.
    Args:
      points: HxWx3 float array of 3D points in world coordinates.
      colors: HxWx3 uint8 array of values in range 0-255 aligned with points.
      bounds: 3x2 float array of values (rows: X,Y,Z; columns: min,max) defining
        region in 3D space to generate heightmap in world coordinates.
      pixel_size: float defining size of each pixel in meters.
    Returns:
      heightmap: HxW float array of height (from lower z-bound) in meters.
      colormap: HxWx3 uint8 array of backprojected color aligned with heightmap.
      xyzmap: HxWx3 float array of XYZ points in world coordinates.
    """
    width = int(np.round((bounds[0, 1] - bounds[0, 0]) / pixel_size))
    height = int(np.round((bounds[1, 1] - bounds[1, 0]) / pixel_size))
    heightmap = np.zeros((height, width), dtype=np.float32)
    colormap = np.zeros((height, width, colors.shape[-1]), dtype=np.uint8)
    xyzmap = np.zeros((height, width, 3), dtype=np.float32)

    # Filter out 3D points that are outside of the predefined bounds.
    ix = (points[Ellipsis, 0] >= bounds[0, 0]) & (points[Ellipsis, 0] < bounds[0, 1])
    iy = (points[Ellipsis, 1] >= bounds[1, 0]) & (points[Ellipsis, 1] < bounds[1, 1])
    iz = (points[Ellipsis, 2] >= bounds[2, 0]) & (points[Ellipsis, 2] < bounds[2, 1])
    valid = ix & iy & iz
    points = points[valid]
    colors = colors[valid]

    # Sort 3D points by z-value, which works with array assignment to simulate
    # z-buffering for rendering the heightmap image.
    iz = np.argsort(points[:, -1])
    points, colors = points[iz], colors[iz]
    px = np.int32(np.floor((points[:, 0] - bounds[0, 0]) / pixel_size))
    py = np.int32(np.floor((points[:, 1] - bounds[1, 0]) / pixel_size))
    px = np.clip(px, 0, width - 1)
    py = np.clip(py, 0, height - 1)
    heightmap[py, px] = points[:, 2] - bounds[2, 0]
    for c in range(colors.shape[-1]):
      colormap[py, px, c] = colors[:, c]
      xyzmap[py, px, c] = points[:, c]
    colormap = colormap[::-1, :, :]  # Flip up-down.
    xv, yv = np.meshgrid(np.linspace(BOUNDS[0, 0], BOUNDS[0, 1], height),
                         np.linspace(BOUNDS[1, 0], BOUNDS[1, 1], width))
    xyzmap[:, :, 0] = xv
    xyzmap[:, :, 1] = yv
    xyzmap = xyzmap[::-1, :, :]  # Flip up-down.
    heightmap = heightmap[::-1, :]  # Flip up-down.
    return heightmap, colormap, xyzmap
  
  def on_top_of(self, obj_a, obj_b):
    """
    check if obj_a is on top of obj_b
    condition 1: l2 distance on xy plane is less than a threshold
    condition 2: obj_a is higher than obj_b
    """
    obj_a_pos = self.get_obj_pos(obj_a)
    
    if obj_b == "table":
      return obj_a_pos[2] < Z_ON_TABLE_TOL_DIST

    obj_b_pos = self.get_obj_pos(obj_b)
    xy_dist = np.linalg.norm(obj_a_pos[:2] - obj_b_pos[:2])
    if obj_b in CORNER_POS:
      is_near = xy_dist < 0.06
      return is_near
    elif 'cylinder' in obj_b:
      is_near = xy_dist < 0.06
      is_higher = obj_a_pos[2] > obj_b_pos[2]
      return is_near and is_higher
    else:
      is_near = xy_dist < 0.04
      is_higher = obj_a_pos[2] > obj_b_pos[2]
      return is_near and is_higher
    
  def is_left_of(self, obj_a, obj_b):
    """
    condition 1: obj_a and obj_b are at the same height
    """
    obj_a_pos = self.get_obj_pos(obj_a)
    obj_b_pos = self.get_obj_pos(obj_b)
    
    x_diff = obj_a_pos[0] - obj_b_pos[0]
    y_dist = np.abs(obj_a_pos[1] - obj_b_pos[1])
    z_dist = np.abs(obj_a_pos[2] - obj_b_pos[2])

    is_left_for_x = x_diff < 0 and np.abs(x_diff) < NEXT_TO_DIST
    is_close_for_y = y_dist < XY_NEXT_TO_TOL_DIST
    is_close_for_z = z_dist < Z_NEXT_TO_TOL_DIST
    return is_left_for_x and is_close_for_y and is_close_for_z

  def is_right_of(self, obj_a, obj_b):
    """
    condition 1: obj_a and obj_b are at the same height
    """
    obj_a_pos = self.get_obj_pos(obj_a)
    obj_b_pos = self.get_obj_pos(obj_b)

    x_diff = obj_a_pos[0] - obj_b_pos[0]
    y_dist = np.abs(obj_a_pos[1] - obj_b_pos[1])
    z_dist = np.abs(obj_a_pos[2] - obj_b_pos[2])

    is_right_for_x = x_diff > 0 and np.abs(x_diff) < NEXT_TO_DIST
    is_close_for_y = y_dist < XY_NEXT_TO_TOL_DIST
    is_close_for_z = z_dist < Z_NEXT_TO_TOL_DIST
    return is_right_for_x and is_close_for_y and is_close_for_z
    

  def is_behind(self, obj_a, obj_b):
    """
    condition 1: obj_a and obj_b are at the same height
    """
    obj_a_pos = self.get_obj_pos(obj_a)
    obj_b_pos = self.get_obj_pos(obj_b)

    x_dist = np.abs(obj_a_pos[0] - obj_b_pos[0])
    y_diff = obj_a_pos[1] - obj_b_pos[1]
    z_dist = np.abs(obj_a_pos[2] - obj_b_pos[2])

    is_in_front_for_y = y_diff > 0 and np.abs(y_diff) < NEXT_TO_DIST
    is_close_for_x = x_dist < XY_NEXT_TO_TOL_DIST
    is_close_for_z = z_dist < Z_NEXT_TO_TOL_DIST
    return is_in_front_for_y and is_close_for_x and is_close_for_z


  def is_in_front_of(self, obj_a, obj_b):
    """
    condition 1: obj_a and obj_b are at the same height
    """
    obj_a_pos = self.get_obj_pos(obj_a)
    obj_b_pos = self.get_obj_pos(obj_b)

    x_dist = np.abs(obj_a_pos[0] - obj_b_pos[0])
    y_diff = obj_a_pos[1] - obj_b_pos[1]
    z_dist = np.abs(obj_a_pos[2] - obj_b_pos[2])

    is_behind_for_y = y_diff < 0 and np.abs(y_diff) < NEXT_TO_DIST
    is_close_for_x = x_dist < XY_NEXT_TO_TOL_DIST
    is_close_for_z = z_dist < Z_NEXT_TO_TOL_DIST
    return is_behind_for_y and is_close_for_x and is_close_for_z
    

  def is_at(self, obj_a, loc):
    """
    Parameters:
      loc - string, must be one of the following: 
        'top left corner', 'top side', 'top right corner', 'left side', 'middle', 'right side', 'bottom left corner',
        'bottom side', 'bottom right corner'
    """
    try:
      loc_pos = CORNER_POS[loc]
      obj_a_pos = self.get_obj_pos(obj_a)
      
      if 'corner' in loc:
        xy_dist = np.linalg.norm(obj_a_pos[:2] - loc_pos[:2])
        return xy_dist < XY_NEXT_TO_TOL_DIST
      else:
          # checking either only the x position or only the y position
          if 'top' in loc or 'bottom' in loc:
            dist = np.abs(obj_a_pos[1] - loc_pos[1])
          else:
            dist = np.abs(obj_a_pos[0] - loc_pos[0])

          if dist < XY_NEXT_TO_TOL_DIST:
            at_top_left_corner = self.is_at(obj_a, 'top left corner')
            at_top_right_corner = self.is_at(obj_a, 'top right corner')
            at_bottom_left_corner = self.is_at(obj_a, 'bottom left corner')
            at_bottom_right_corner = self.is_at(obj_a, 'bottom right corner')
            if 'top' in loc:
                return (not at_top_left_corner) and (not at_top_right_corner)
            elif 'bottom' in loc:
                return (not at_bottom_left_corner) and (not at_bottom_right_corner)
            elif 'left' in loc:
                return (not at_top_left_corner) and (not at_bottom_left_corner)
            elif 'right' in loc:
                return (not at_top_right_corner) and (not at_bottom_right_corner)
            else:
                return False
          else:
            return False
    except:
      print(f"'{loc}' is an invalid location to query")
      return False
    
  
  def has_changed_initial_pos(self, obj_a):
    init_pos = self.init_pos[obj_a]
    curr_pos = self.get_obj_pos(obj_a)

    init_pos_xy = init_pos[:2]
    init_pos_z = init_pos[2]
    curr_pos_xy = curr_pos[:2]
    curr_pos_z = curr_pos[2]

    return np.abs(np.sum(init_pos_xy - curr_pos_xy)) > NOT_MOVED_TOL_DIST or np.abs(init_pos_z - curr_pos_z) > NOT_MOVED_TOL_DIST_Z


  def get_obj_id(self, obj_name):
    try:
      if obj_name in self.obj_name_to_id:
        obj_id = self.obj_name_to_id[obj_name]
      else:
        obj_name = obj_name.replace('circle', 'cylinder').replace('square', 'block').replace('small', '').strip()
        obj_id = self.obj_name_to_id[obj_name]
    except:
      print(f'requested_name="{obj_name}"')
      print(f'available_objects_and_id="{self.obj_name_to_id}')
    return obj_id
  
  def get_obj_pos(self, obj_name):
    obj_name = obj_name.replace('the', '').replace('_', ' ').strip()
    if obj_name in CORNER_POS:
      position = np.float32(np.array(CORNER_POS[obj_name]))
    elif obj_name == "table":
      # randomly generate a position to place that is a safe distance from other objects

      # first, collect the current distance of objects
      curr_objs_xyz = np.zeros((0, 3))
      for obj in self.object_list:
        obj_pos = self.get_obj_pos(obj)
        curr_objs_xyz = np.concatenate((curr_objs_xyz, np.expand_dims(obj_pos, axis=0)), axis=0)
      
      position, _ = self.init_random_obj_postion(obj_xyz_old=curr_objs_xyz, min_dist=self._on_table_min_dist_btw_objs)
    else:
      pick_id = self.get_obj_id(obj_name)
      pose = pybullet.getBasePositionAndOrientation(pick_id)
      position = np.float32(pose[0])
    return position
  
  def get_bounding_box(self, obj_name):
    obj_id = self.get_obj_id(obj_name)
    return pybullet.getAABB(obj_id)
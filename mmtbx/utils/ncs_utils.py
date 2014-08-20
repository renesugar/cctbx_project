from __future__ import division
from mmtbx.utils.map_correlation import Map_correlation
from scitbx.array_family import flex
import mmtbx.monomer_library.server
from mmtbx import monomer_library
from scitbx import matrix
import scitbx.rigid_body
from cctbx import xray
import random
import math


def concatenate_rot_tran(transforms_obj=None,
                         ncs_restraints_group_list=None):
  """
  Concatenate rotation angles, corresponding to the rotation
  matrices and scaled translation vectors to a single long flex.double object

  Parameters:
    transforms_obj : (mmtbx.refinement.minimization_ncs_constraints
      ncs_group_object) containing information on Rotation matrices (lists of
      objects matrix.rec) and Translation vectors (lists of objects matrix.rec)
    ncs_restraints_group_list : a list of ncs_restraint_group objects

  Returns:
    flex.double : [(alpha_1,beta_1,gamma_1,Tx_1,Ty_1,Tz_1)...]
  """
  x = []
  if (not ncs_restraints_group_list) and transforms_obj:
    ncs_restraints_group_list = transforms_obj.get_ncs_restraints_group_list()
  if ncs_restraints_group_list:
    for gr in ncs_restraints_group_list:
      for tr in gr.copies:
        x.extend(list(rotation_to_angles(rotation=tr.r.elems))
                 + list(tr.t.elems))
  return flex.double(x)

def get_rotation_translation_as_list(transforms_obj=None,
                                     ncs_restraints_group_list=None):
  """
  Collect and returns rotations matrices and translations vectors to two lists
  """
  r = []
  t = []
  if (not ncs_restraints_group_list) and transforms_obj:
    ncs_restraints_group_list = transforms_obj.get_ncs_restraints_group_list()
  if ncs_restraints_group_list:
    for nrg in ncs_restraints_group_list:
      for tr in nrg.copies:
        r.append(tr.r)
        t.append(tr.t)
  return r,t

def update_transforms(transforms_obj,rm,tv):
  """ Update transforms_obj with the rotation matrices (rm) and translation
  vectors (tv) """
  assert len(transforms_obj.transform_order) == len(rm)
  assert len(rm) == len(tv)
  for tr,r,t in zip(transforms_obj.transform_order,rm,tv):
    transforms_obj.ncs_transform[tr].r = r
    transforms_obj.ncs_transform[tr].t = t
  return transforms_obj

def update_ncs_restraints_group_list(ncs_restraints_group_list,rm,tv):
  """ Update ncs_restraints_group_list with the rotation matrices (rm) and
  translation vectors (tv) """
  assert len(rm) == len(tv)
  new_list = []
  for gr in ncs_restraints_group_list:
    for tr in gr.copies:
      tr.r = rm.pop(0)
      tr.t = tv.pop(0)
    new_list.append(gr)
  return new_list

def update_rot_tran(x,transforms_obj=None,ncs_restraints_group_list=None):
  """
  Convert the refinable parameters, rotations angles and
  scaled translations, back to rotation matrices and translation vectors and
  updates the transforms_obj (ncs_restraints_group_list)

  Parameters:
    x : a flex.double of the form (theta_1,psi_1,phi_1,tx_1,ty_1,tz_1,..
      theta_n,psi_n,phi_n,tx_n/s,ty_n/s,tz_n/s). where n is the number of
      transformations.
    transforms_obj : (ncs_group_object) containing information on Rotation
      matrices, Translation vectors and NCS
  ncs_restraints_group_list : a list of ncs_restraint_group objects

  Returns:
    The same type of input object with converted transforms
  """
  assert bool(transforms_obj) == (not bool(ncs_restraints_group_list))
  if transforms_obj:
    ncs_restraints_group_list = transforms_obj.get_ncs_restraints_group_list()
  if ncs_restraints_group_list:
    i = 0
    for gr in ncs_restraints_group_list:
      copies = []
      for tr in gr.copies:
        the,psi,phi =x[i*6:i*6+3]
        rot = scitbx.rigid_body.rb_mat_xyz(
          the=the, psi=psi, phi=phi, deg=False)
        tran = matrix.rec(x[i*6+3:i*6+6],(3,1))
        tr.r = (rot.rot_mat())
        tr.t = tran
        copies.append(tr)
        i += 1
      gr.copies = copies
    if transforms_obj:
      transforms_obj.update_using_ncs_restraints_group_list(
        ncs_restraints_group_list)
      return transforms_obj
    else:
      return ncs_restraints_group_list

def rotation_to_angles(rotation, deg=False):
  """
  Get the rotation angles around the axis x,y,x for rotation r
  Such that r = Rx*Ry*Rz

  Note that typically there are two solutions, and this function will return
  only one. In the case that cos(beta) == 0 there are infinite number of
  solutions, the function returns the one where gamma = 0

  Parameters:
    r : (flex.double) of the form (Rxx,Rxy,Rxz,Ryx,Ryy,Ryz,Rzx,Rzy,Rzz)
    deg : When False use radians, when True use degrees

  Returns:
    angles: (flex.double) containing rotation angles in  the form
      (alpha, beta, gamma)
  """
  # make sure the rotation data type is flex.double
  if not isinstance(rotation,type(flex.double())):
    rotation = flex.double(rotation)
  (Rxx,Rxy,Rxz,Ryx,Ryy,Ryz,Rzx,Rzy,Rzz) = rotation.round(8)
  if Rxz not in [1,-1]:
    beta = math.asin(Rxz)
    # beta2 = math.pi - beta
    # using atan2 to take into account the possible different angles and signs
    alpha = math.atan2(-Ryz/math.cos(beta),Rzz/math.cos(beta))
    gamma = math.atan2(-Rxy/math.cos(beta),Rxx/math.cos(beta))
    # alpha2 = math.atan2(-Ryz/math.cos(beta2),Rzz/math.cos(beta2))
    # gamma2 = math.atan2(-Rxy/math.cos(beta2),Rxx/math.cos(beta2))
  elif Rxz == 1:
    beta = math.pi/2
    alpha = math.atan2(Ryx,Ryy)
    gamma = 0
  elif Rxz == -1:
    beta = -math.pi/2
    alpha = math.atan2(-Ryx,Ryy)
    gamma = 0
  else:
    raise ArithmeticError("Can't calculate rotation angles")

  angles = flex.double((alpha,beta,gamma))
  # angles2 = flex.double((alpha2,beta2,gamma2))

  if deg:
    # Convert to degrees
    angles = 180*angles/math.pi
    angles = angles.round(5)
    # angles2 = 180*angles2/math.pi
  return angles

def angles_to_rotation(angles_xyz, deg=False, rotation_is_tuple=False):
  """
  Calculate rotation matrix R, such that R = Rx(alpha)*Ry(beta)*Rz(gamma)

  Parameters:
    angles_xyz : (flex.double) (alpha,beta,gamma)
    deg : (bool) When False use radians, when True degrees
    rotation_is_tuple : (bool) when False, return flxe.double object,
      when True return tuple

  Returns:
  R : (tuple or flex.double) the components of a rotation matrix
  """
  assert len(angles_xyz) == 3
  alpha,beta,gamma = angles_xyz
  rot = scitbx.rigid_body.rb_mat_xyz(the=alpha, psi=beta, phi=gamma, deg=deg)
  R = rot.rot_mat()
  # adjust rounding to angle format
  if deg: i = 6
  else: i = 8
  if rotation_is_tuple:
    return R.round(i).elems
  else:
    return flex.double(R.round(i))

def shake_transformations(x,
                          shake_angles_sigma      = 0.035,
                          shake_translation_sigma = 0.5):
  """
  Shake rotation matrices and translation vectors of a rotation matrices and
  translation vectors from the MTRIX records in a PDB file.

  Parameters:
    x (flex.double): [(alpha_1,beta_1,gamma_1,Tx_1/s,Ty_1/s,Tz_1/s)...]
    shake_angles_sigma (float): the sigma (in radians) of the random gaussian
      shaking of the rotation angles
    shake_translation_sigma (float): the sigma (in angstrom) of the random
      gaussian shaking of the translation

  Return:
    new_x (flex.double): The shaken x
  """
  new_x = flex.double()
  for i in xrange(0,len(x),6):
    new_x.append(random.gauss(x[i+0],shake_angles_sigma))
    new_x.append(random.gauss(x[i+1],shake_angles_sigma))
    new_x.append(random.gauss(x[i+2],shake_angles_sigma))
    new_x.append(random.gauss(x[i+3],shake_translation_sigma))
    new_x.append(random.gauss(x[i+4],shake_translation_sigma))
    new_x.append(random.gauss(x[i+5],shake_translation_sigma))
  return new_x

def compute_transform_grad(grad_wrt_xyz,
                           xyz_asu,
                           x,
                           ncs_restraints_group_list=None,
                           transforms_obj=None):
  """
  Compute gradient in respect to the rotation angles and the translation
  vectors. R = Rx(the)Ry(psi)Rz(phi)

  Parameters:
    grad_wrt_xyz (flex.double): gradients with respect to xyz.
    ncs_restraints_group_list: list containing ncs_restraint_group objects
    transforms_obj (ncs_group_object): containing information in rotation
      matrices and to which chains they apply
    xyz_asu (flex.vec3): The coordinates sites cart of the complete ASU
    x (flex double): The angles, in the form
      (theta_1,psi_1,phi_1,tx_1,ty_1,tz_1,..
      theta_n,psi_n,phi_n,tx_n/s,ty_n/s,tz_n/s)

  Returns:
  g (flex.double): the gradient
  """
  assert bool(transforms_obj) == (not bool(ncs_restraints_group_list))
  if transforms_obj:
    ncs_restraints_group_list = transforms_obj.get_ncs_restraints_group_list()
  g = []
  grad_wrt_xyz = flex.vec3_double(grad_wrt_xyz)
  i = 0
  for nrg in ncs_restraints_group_list:
    xyz_ncs_transform = xyz_asu.select(nrg.master_iselection)
    xyz_len = xyz_ncs_transform.size()
    # calc the coordinates of the master NCS at its coordinates center system
    mu_c = flex.vec3_double([xyz_ncs_transform.sum()]) * (1/xyz_len)
    xyz_cm = xyz_ncs_transform - flex.vec3_double(list(mu_c) * xyz_len)
    for nrg_copy in nrg.copies:
      grad_ncs_wrt_xyz = grad_wrt_xyz.select(nrg_copy.copy_iselection)
      assert xyz_len == grad_ncs_wrt_xyz.size()
      grad_wrt_t = list(grad_ncs_wrt_xyz.sum())
      # Sum angles gradient over the coordinates
      # Use the coordinate center for rotation
      m = grad_ncs_wrt_xyz.transpose_multiply(xyz_cm)
      m = matrix.sqr(m)
      # Calculate gradient with respect to the rotation angles
      the,psi,phi = x[i*6:i*6+3]
      rot = scitbx.rigid_body.rb_mat_xyz(
        the=the, psi=psi, phi=phi, deg=False)
      g_the = (m * rot.r_the().transpose()).trace()
      g_psi = (m * rot.r_psi().transpose()).trace()
      g_phi = (m * rot.r_phi().transpose()).trace()
      g.extend([g_the, g_psi, g_phi])
      g.extend(grad_wrt_t)
      i += 1
  return flex.double(g)

def get_ncs_sites_cart(ncs_obj=None,
                       fmodel=None,
                       xray_structure=None,
                       sites_cart=None,
                       extended_ncs_selection=None):
  """
  Parameters:
    ncs_obj: an object that contains fmodel, sites_cart or xray_structure
      and an atom selection flags for a single NCS copy.

  Returns:
    (flex.vec3): coordinate sites cart of the single NCS copy
  """
  if ncs_obj:
    if hasattr(ncs_obj, 'extended_ncs_selection'):
      extended_ncs_selection = ncs_obj.extended_ncs_selection
    else:
      assert extended_ncs_selection
    if hasattr(ncs_obj, 'sites_cart'):
      return ncs_obj.sites_cart().select(extended_ncs_selection)
    elif hasattr(ncs_obj, 'fmodel'):
      xrs_one_ncs = ncs_obj.fmodel.xray_structure.select(extended_ncs_selection)
      return xrs_one_ncs.sites_cart()
    elif  hasattr(ncs_obj, 'xray_structure') or xray_structure:
      xrs_one_ncs = ncs_obj.xray_structure.sites_cart()
      return xrs_one_ncs.select(extended_ncs_selection)
  else:
    if sites_cart:
      return sites_cart().select(extended_ncs_selection)
    elif fmodel:
      xrs_one_ncs = fmodel.xray_structure.select(extended_ncs_selection)
      return xrs_one_ncs.sites_cart()
    elif  xray_structure:
      xrs_one_ncs = xray_structure.sites_cart()
      return xrs_one_ncs.select(extended_ncs_selection)


def get_weight(minimization_obj=None,
               fmodel=None,
               grm=None,
               sites=None,
               transformations=None,
               u_iso=None,
               ncs_restraints_group_list=None,
               refine_selection=None):
  """
  Calculates weights for refinements

  :param minimization_obj:Minimization object containing all the other
    parameters
  :param sites (bool): Refine by sites
  :param u_iso (bool): Refine using u_iso
  :param transformations (bool): Refine using transformations
  :param rotations, translations (matrix objects):
  :param grm: Restraints manager
  :param iso_restraints: (libtbx.phil.scope_extract) object used for u_iso
    refinement parameters
  :param ncs_atom_selection: (flex bool) for a single ncs atom selection

  :returns weight (int):
  """
  if minimization_obj:
    mo = minimization_obj
    fmodel = mo.fmodel
    grm = mo.grm
    sites = mo.sites
    transformations = mo.transformations
    u_iso = mo.u_iso
    ncs_restraints_group_list = mo.ncs_restraints_group_list
    extended_ncs_selection = mo.extended_ncs_selection
  else:
    extended_ncs_selection = get_extended_ncs_selection(
      ncs_restraints_group_list=ncs_restraints_group_list,
      refine_selection=refine_selection)

  have_transforms = ncs_restraints_group_list != []
  assert [sites,u_iso,transformations].count(True)==1
  fmdc = fmodel.deep_copy()
  if sites:
    fmdc.xray_structure.shake_sites_in_place(mean_distance=0.3)
  elif u_iso:
    fmdc.xray_structure.shake_adp()
  elif transformations and have_transforms:
    x = concatenate_rot_tran(
      ncs_restraints_group_list = ncs_restraints_group_list)
    x = shake_transformations(
      x = x,
      shake_angles_sigma=0.035,
      shake_translation_sigma=0.5)
  fmdc.update_xray_structure(xray_structure = fmdc.xray_structure,
    update_f_calc=True)
  fmdc.xray_structure.scatterers().flags_set_grads(state=False)
  if sites:
    xray.set_scatterer_grad_flags(
      scatterers = fmdc.xray_structure.scatterers(),
      site       = True)
    # fmodel gradients
    gxc = flex.vec3_double(fmdc.one_time_gradients_wrt_atomic_parameters(
      site = True).packed())
    # manager restraints, energy sites gradients
    gc = grm.energies_sites(
      sites_cart        = fmdc.xray_structure.sites_cart(),
      compute_gradients = True).gradients
  elif u_iso:
    # Create energies_site gradient, to create
    # geometry_restraints_manager.plain_pair_sym_table
    # needed for the energies_adp_iso
    import mmtbx.refinement.adp_refinement
    temp = mmtbx.refinement.adp_refinement.adp_restraints_master_params
    iso_restraints = temp.extract().iso
    gc = grm.energies_sites(
      sites_cart        = fmdc.xray_structure.sites_cart(),
      compute_gradients = True).gradients
    xray.set_scatterer_grad_flags(
      scatterers = fmdc.xray_structure.scatterers(),
      u_iso      = True)
    # fmodel gradients
    gxc = fmdc.one_time_gradients_wrt_atomic_parameters(
      u_iso = True).as_double()
    # manager restraints, energy sites gradients
    gc = grm.energies_adp_iso(
      xray_structure    = fmdc.xray_structure,
      parameters        = iso_restraints,
      use_u_local_only  = iso_restraints.use_u_local_only,
      use_hd            = False,
      compute_gradients = True).gradients
  elif transformations and have_transforms:
    xyz_ncs = get_ncs_sites_cart(
      fmodel=fmodel, extended_ncs_selection=extended_ncs_selection)
    xray.set_scatterer_grad_flags(
      scatterers = fmdc.xray_structure.scatterers(),
      site       = True)
    # fmodel gradients
    gxc_xyz = flex.vec3_double(fmdc.one_time_gradients_wrt_atomic_parameters(
      site = True).packed())
    # manager restraints, energy sites gradients
    gc_xyz = grm.energies_sites(
      sites_cart        = fmdc.xray_structure.sites_cart(),
      compute_gradients = True).gradients
    gxc = compute_transform_grad(
      grad_wrt_xyz      = gxc_xyz.as_double(),
      ncs_restraints_group_list = ncs_restraints_group_list,
      xyz_asu           = fmdc.xray_structure.sites_cart(),
      x                 = x)
    gc = compute_transform_grad(
      grad_wrt_xyz      = gc_xyz.as_double(),
      ncs_restraints_group_list = ncs_restraints_group_list,
      xyz_asu           = fmdc.xray_structure.sites_cart(),
      x                 = x)

  weight = 1.
  gc_norm  = gc.norm()
  gxc_norm = gxc.norm()
  if(gxc_norm != 0.0):
    weight = gc_norm / gxc_norm

  weight =min(weight,1e6)
  return weight

def get_restraints_manager(pdb_file_name=None,pdb_string=None):
  """  Generate restraint manager from a PDB file or a PDB string  """
  assert [pdb_file_name,pdb_string].count(None)==1
  mon_lib_srv = monomer_library.server.server()
  ener_lib = monomer_library.server.ener_lib()
  if pdb_string: pdb_lines = pdb_string.splitlines()
  else: pdb_lines = None
  processed_pdb_file = monomer_library.pdb_interpretation.process(
    mon_lib_srv    = mon_lib_srv,
    ener_lib       = ener_lib,
    file_name      = pdb_file_name,
    raw_records    = pdb_lines,
    force_symmetry = True)
  geometry = processed_pdb_file.geometry_restraints_manager(
    show_energies = False, plain_pairs_radius = 5.0)
  return mmtbx.restraints.manager(
    geometry = geometry, normalization = False)

def apply_transforms(ncs_coordinates,
                     ncs_restraints_group_list,
                     total_asu_length,
                     extended_ncs_selection,
                     round_coordinates = True,
                     center_of_coordinates = None):
  """
  Apply transformation to ncs_coordinates,
  and round the results if round_coordinates is True

  Parameters:
    ncs_coordinates (flex.vec3): master ncs coordinates
    ncs_restraints_group_list: list of ncs_restraint_group objects
    total_asu_length (int): Complete ASU length
      extended_ncs_selection (flex.size_t): master ncs and non-ncs related parts
    center_of_coordinates : when not None, contains the center of coordinate of
      the master for each ncs copy

  Returns:
    (flex.vec3_double): Asymmetric or biological unit parts that are related via
    ncs operations
  """
  asu_xyz = flex.vec3_double([(0,0,0)]*total_asu_length)
  asu_xyz.set_selected(extended_ncs_selection,ncs_coordinates)

  # get the rotation and translation for the native coordinate system
  if bool(center_of_coordinates):
    ncs_restraints_group_list = shift_translation_back_to_place(
      shifts = center_of_coordinates,
      ncs_restraints_group_list = ncs_restraints_group_list)
  for nrg in ncs_restraints_group_list:
    master_ncs_selection = nrg.master_iselection
    for ncs_copy in nrg.copies:
      copy_selection = ncs_copy.copy_iselection
      ncs_xyz = asu_xyz.select(master_ncs_selection)
      new_sites = ncs_copy.r.elems * ncs_xyz + ncs_copy.t
      asu_xyz.set_selected(copy_selection,new_sites)
  if round_coordinates:
    return flex.vec3_double(asu_xyz).round(3)
  else:
    return flex.vec3_double(asu_xyz)

def get_extended_ncs_selection(ncs_restraints_group_list,refine_selection):
  """
  :param ncs_restraints_group_list: list of ncs_restraint_group objects
  :param refine_selection (flex.siz_t): of all ncs related copies and
    non ncs related parts to be included in selection
  :return (flex.siz_t): selection of all ncs groups master ncs selection and
    non ncs related portions that are being refined
  """
  refine_selection = set(refine_selection)
  total_master_ncs_selection = set()
  total_ncs_related_selection = set()
  for nrg in ncs_restraints_group_list:
    master_ncs_selection = nrg.master_iselection
    total_master_ncs_selection.update(set(master_ncs_selection))
    for ncs_copy in nrg.copies:
      asu_selection = ncs_copy.copy_iselection
      total_ncs_related_selection.update(set(asu_selection))
  # make sure all ncs related parts are in refine_selection
  all_ncs = total_master_ncs_selection | total_ncs_related_selection
  msg = 'refine_selection does not contain all ncs related atoms'
  assert not bool(all_ncs - refine_selection), msg
  #
  extended_ncs_selection = refine_selection - total_ncs_related_selection
  return flex.size_t(list(extended_ncs_selection))

def get_ncs_related_selection(ncs_restraints_group_list,asu_size):
  """
  :param ncs_restraints_group_list (list): list of ncs_restraint_group objects
  :param asu_size (int): the total size of the ASU
  :return selection (flex.bool): selection of all ncs related atom in the ASU
  """
  total_master_ncs_selection = set()
  total_ncs_related_selection = set()
  for nrg in ncs_restraints_group_list:
    master_ncs_selection = nrg.master_iselection
    total_master_ncs_selection.update(set(master_ncs_selection))
    for ncs_copy in nrg.copies:
      asu_selection = ncs_copy.copy_iselection
      total_ncs_related_selection.update(set(asu_selection))
  #
  total_ncs_related_selection.update(total_master_ncs_selection)
  ts = flex.size_t(list(total_ncs_related_selection))
  selection = flex.bool(asu_size, ts)
  return selection

def shift_translation_to_center(shifts, ncs_restraints_group_list):
  """
  Add shifts to the translation component of ncs_restraints_group_list
  towards the center of coordinates
  :param shifts (list): [mu_1, mu_1, mu_2...] where the mu stands
    for the shift of the master copy to the coordinate center mu is (dx,dy,dz)
  :param ncs_restraints_group_list (list): ncs_restraints_group_list
  :return ncs_restraints_group_list (list):
  """
  if bool(shifts):
    new_list = ncs_restraints_group_list_copy(ncs_restraints_group_list)
    i = 0
    for nrg in new_list:
      for ncs_copy in nrg.copies:
        mu = shifts[i]
        i += 1
        # Only the translation is changing
        t = ncs_copy.r.elems * mu + ncs_copy.t - mu
        ncs_copy.t = matrix.col(t[0])
  return new_list

def shift_translation_back_to_place(shifts, ncs_restraints_group_list):
  """
  shifts to the translation component of ncs_restraints_group_list from the
  center of coordinates back to place
  :param shifts (list): [mu_1, mu_1, mu_2...] where the mu stands
    for the shift of the master copy to the coordinate center mu is (dx,dy,dz)
  :param ncs_restraints_group_list: ncs_restraints_group_list
  :return new_list (list): list of ncs_restraints_group objects
  """
  if bool(shifts):
    i = 0
    new_list = ncs_restraints_group_list_copy(ncs_restraints_group_list)
    for nrg in new_list:
      for ncs_copy in nrg.copies:
        mu = shifts[i]
        i += 1
        # Only the translation is changing
        t = mu - ncs_copy.r.elems * mu + ncs_copy.t
        ncs_copy.t = matrix.col(t[0])
  else:
    new_list = ncs_restraints_group_list
  return new_list

def get_ncs_gorups_centers(xray_structure, ncs_restraints_group_list):
  """
  calculate the center of coordinate for the master of each ncs copy

  :param xray_structure:
  :param ncs_restraints_group_list:
  :return shifts (list): [mu_1, mu_1, mu_2...] where the mu stands
    for the shift of the master copy to the coordinate center mu is (dx,dy,dz)
  """
  shifts = []
  asu_xyz = xray_structure.sites_cart()
  for nrg in ncs_restraints_group_list:
    master_ncs_selection = nrg.master_iselection
    master_xyz = asu_xyz.select(master_ncs_selection)
    mu_m = matrix.col(master_xyz.sum()) / len(master_ncs_selection)
    mu_m = flex.vec3_double([mu_m.elems])
    for ncs_copy in nrg.copies:
      shifts.append(mu_m)
  return shifts

def ncs_restraints_group_list_copy(ncs_restraints_group_list):
  """
  Deep copy of ncs_restraints_group_list

  Args:
    ncs_restraints_group_list: list of ncs_restraint_group

  Returns:
    new_list: a deep copy of ncs_restraints_group_list
  """
  from iotbx.ncs.ncs_preprocess import ncs_restraint_group
  from iotbx.ncs.ncs_preprocess import ncs_copy
  new_list = []
  for nrg in ncs_restraints_group_list:
    new_nrg = ncs_restraint_group(nrg.master_iselection)
    for ncs in nrg.copies:
      new_ncs_copy = ncs_copy(
        copy_iselection=ncs.copy_iselection,
        rot=ncs.r,
        tran=ncs.t)
      new_nrg.copies.append(new_ncs_copy)
    new_list.append(new_nrg)
  return new_list

def ncs_groups_selection(ncs_restraints_group_list,selection):
  """
  Modifies the selections of master and copies according the "selection"
  - Keep the order of selected atoms
  - Keep only atoms that appear in master and ALL copies
  Also modify "selection" to include ncs related atoms only if selected in
  both master and ALL ncs copies

  :param ncs_restraints_group_list (list): list of ncs_restraints_group objects
  :param selection (flex.bool or flex.size_t): atom selection
  :return new_nrg_list (list): list of modified ncs_restraints_group objects
  :return selection (flex.size_t): modified selection
  """
  if isinstance(selection,flex.bool): selection = selection.iselection()
  sel_set = set(selection)
  new_nrg_list = ncs_restraints_group_list_copy(ncs_restraints_group_list)
  # check what are the selection that shows in both master and all copies
  for nrg in new_nrg_list:
    m = set(nrg.master_iselection)
    m_list = [(pos,indx) for pos,indx in enumerate(list(nrg.master_iselection))]
    m_in_sel = m.intersection(sel_set)
    common_selection_pos = {pos for (pos,indx) in m_list if indx in m_in_sel}
    for ncs in nrg.copies:
      c = set(ncs.copy_iselection)
      c_list = [(pos,indx) for pos,indx in enumerate(list(ncs.copy_iselection))]
      copy_in_sel = c.intersection(sel_set)
      include_set = {pos for (pos,indx) in c_list if indx in copy_in_sel}
      common_selection_pos.intersection_update(include_set)
      if not bool(common_selection_pos): break
    # use the common_selection_pos to update all selections
    nrg.master_iselection, not_included = selected_positions(
      nrg.master_iselection,common_selection_pos)
    selection = remove_items_from_selection(selection,not_included)
    for ncs in nrg.copies:
      ncs.copy_iselection, not_included = selected_positions(
        ncs.copy_iselection,common_selection_pos)
      selection = remove_items_from_selection(selection,not_included)

  return new_nrg_list, selection


def selected_positions(selection,positions):
  """
  Returns only the selected indices in the positions specified in "positions"
  keeping the order

  :param selection (flex.size_t): Atoms selection
  :param positions (set or list): the allowed positions in the selections
  :return (flex.size_t, flex.size_t): (selected atoms, atoms, not selected)

  Examples:
  ---------
  >>>a = flex.size_t([1,2,5,6,4])
  >>>pos = {0,3,4}
  >>>s,d = selected_positions(a,pos)
  >>>list(s)
  [1,6,4]
  >>>list(d)
  [2,5]
  """
  assert isinstance(selection,flex.size_t)
  if isinstance(positions,set): positions = flex.size_t(list(positions))
  if isinstance(positions,list): positions = flex.size_t(positions)
  include = flex.bool(selection.size(),positions)
  not_include = ~include
  return selection.select(include), selection.select(not_include)

def remove_items_from_selection(selection,remove):
  """
  Remove a set of atoms from "selection"

  :param selection (flex.size_t): atom selection
  :param remove (flex.size_t): atoms to remove from selection
  :return (flex.size_t): modified atom selection

  Examples:
  ---------
  >>>a = flex.size_t([1,2,5,6,4])
  >>>r = flex.size_t([2,5])
  >>>s = remove_items_from_selection(a,r,10)
  >>>list(s)
  [1,6,4]
  """
  selection = list(selection)
  remove = set(remove)
  new_selection = [x for x in selection if not (x in remove)]
  return flex.size_t(new_selection)

def change_ncs_groups_master(ncs_restraints_group_list,new_masters):
  """
  Switch master NCS copy with one of the copies, as specified in the new_masters

  Args:
    ncs_restraints_group_list: list of ncs restraints group objects
    new_masters (list of integers): the number of the copy, in each group,
    that will become the new master

  Returns:
    Modified ncs_restraints_group_list
  """
  assert isinstance(new_masters,list)
  assert len(ncs_restraints_group_list) == len(new_masters)

  for nrg,c in zip(ncs_restraints_group_list,new_masters):
    # c for the master is 0 and for the first copy is 1
    if c == 0: continue
    c_i = c - 1
    # switch master and copy selection
    nrg.master_iselection, nrg.copies[c_i].copy_iselection = \
      nrg.copies[c_i].copy_iselection, nrg.master_iselection
    # Adjust rotation ans translation
    r = nrg.copies[c_i].r = (nrg.copies[c_i].r.transpose())
    t = nrg.copies[c_i].t = (- nrg.copies[c_i].r * nrg.copies[c_i].t)
    # change selected copy
    for i,ncs in enumerate(nrg.copies):
      if i != c_i:
        # change translation before rotation
        nrg.copies[i].t = (nrg.copies[i].r * t + nrg.copies[i].t)
        nrg.copies[i].r = (nrg.copies[i].r * r)
  return ncs_restraints_group_list


def get_list_of_best_ncs_copy_map_correlation(
        ncs_restraints_group_list,
        xray_structure=None,
        fmodel=None,
        map_data=None,
        d_min=1.0):
  """
  Finds the copy with best map correlation in each ncs group

  Args:
    ncs_restraints_group_list: list of ncs restraints group objects
    xray_structure (object):
    fmodel (object):
    map_data (object):
    d_min (float): min data resolution

  Returns:
    best_list (list of int): list of the copy with the best map correlation.
    (the master copy is 0)
  """
  best_list = []
  mp = Map_correlation(
    xray_structure = xray_structure,
    fmodel         = fmodel,
    map_data       = map_data,
    d_min          = d_min)

  for nrg in ncs_restraints_group_list:
    selections = []
    selections.append(nrg.master_iselection)
    for ncs in nrg.copies:
      selections.append(ncs.copy_iselection)
    cc = mp.calc_correlation_coefficient(selections)
    best_list.append(cc.index(max(cc)))
  return best_list

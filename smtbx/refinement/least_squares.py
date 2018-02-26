from __future__ import division, absolute_import, print_function
import boost.python
ext = boost.python.import_ext("smtbx_refinement_least_squares_ext")
from smtbx_refinement_least_squares_ext import *


import smtbx.refinement.weighting_schemes # import dependency
from cctbx import xray
from libtbx import adopt_optional_init_args
from scitbx import linalg
from scitbx.lstbx import normal_eqns
from scitbx.array_family import flex
from smtbx.structure_factors import direct
from smtbx.refinement.restraints import origin_fixing_restraints

import math

class crystallographic_ls(
  normal_eqns.non_linear_ls_with_separable_scale_factor):

  default_weighting_scheme = mainstream_shelx_weighting
  weighting_scheme = "default"
  origin_fixing_restraints_type = (
    origin_fixing_restraints.atomic_number_weighting)
  f_mask = None
  restraints_manager=None
  n_restraints = None
  initial_scale_factor = None

  def __init__(self, observations, reparametrisation,
               **kwds):
    super(crystallographic_ls, self).__init__(reparametrisation.n_independents)
    self.observations = observations
    self.reparametrisation = reparametrisation
    adopt_optional_init_args(self, kwds)
    if self.f_mask is not None:
      assert self.f_mask.size() == observations.fo_sq.size()
    self.one_h_linearisation = direct.f_calc_modulus_squared(
      self.xray_structure)
    if self.weighting_scheme == "default":
      self.weighting_scheme = self.default_weighting_scheme()
    self.origin_fixing_restraint = self.origin_fixing_restraints_type(
      self.xray_structure.space_group())
    self.taken_step = None
    self.restraints_normalisation_factor = None

  @property
  def xray_structure(self):
    return self.reparametrisation.structure

  @property
  def twin_fractions(self):
    return self.reparametrisation.twin_fractions

  def build_up(self, objective_only=False):
    if self.f_mask is not None:
      f_mask = self.f_mask.data()
    else:
      f_mask = flex.complex_double()

    extinction_correction = self.reparametrisation.extinction
    if extinction_correction is None:
      extinction_correction = xray.dummy_extinction_correction()

    def args(scale_factor, weighting_scheme, objective_only):
      args = (self,
              self.observations,
              f_mask,
              weighting_scheme,
              scale_factor,
              self.one_h_linearisation,
              self.reparametrisation.jacobian_transpose_matching_grad_fc(),
              extinction_correction
              )
      if objective_only:
        args += (True,)
      return args

    if not self.finalised: #i.e. never been called
      self.reparametrisation.linearise()
      self.reparametrisation.store()
      scale_factor = self.initial_scale_factor
      if scale_factor is None: # we haven't got one from previous refinement
        result = ext.build_normal_equations(
          *args(scale_factor=None, weighting_scheme=sigma_weighting(),
                objective_only=True))
        scale_factor = self.scale_factor()
    else: # use scale factor from the previous step
      scale_factor = self.scale_factor()

    self.reset()
    result = ext.build_normal_equations(*args(scale_factor,
                                              self.weighting_scheme,
                                              objective_only))
    self.f_calc = self.observations.fo_sq.array(
      data=result.f_calc(), sigmas=None)
    self.fc_sq = self.observations.fo_sq.array(
      data=result.observables(), sigmas=None)\
        .set_observation_type_xray_intensity()
    self.weights = result.weights()
    self.objective_data_only = self.objective()
    self.chi_sq_data_only = self.chi_sq()
    if self.restraints_manager is not None:
      # Here we determine a normalisation factor to place the restraints on the
      # same scale as the average residual. This is the normalisation
      # factor suggested in Giacovazzo and similar to that used by shelxl.
      # (shelx manual, page 5-1).
      # The factor 2 comes from the fact that we minimize 1/2 sum w delta^2
      if self.restraints_normalisation_factor is None:
        self.restraints_normalisation_factor \
            = 2 * self.objective_data_only/(self.n_equations-self.n_parameters)
      linearised_eqns = self.restraints_manager.build_linearised_eqns(
        self.xray_structure, self.reparametrisation.parameter_map())
      jacobian = \
        self.reparametrisation.jacobian_transpose_matching(
          self.reparametrisation.mapping_to_grad_fc_all).transpose()
      self.reduced_problem().add_equations(
        linearised_eqns.deltas,
        linearised_eqns.design_matrix * jacobian,
        linearised_eqns.weights * self.restraints_normalisation_factor)
      self.n_restraints = linearised_eqns.n_restraints()
      self.chi_sq_data_and_restraints = self.chi_sq()
    if not objective_only:
      self.origin_fixing_restraint.add_to(
        self.step_equations(),
        self.reparametrisation.jacobian_transpose_matching_grad_fc(),
        self.reparametrisation.asu_scatterer_parameters)

  def parameter_vector_norm(self):
    return self.reparametrisation.norm_of_independent_parameter_vector

  def scale_factor(self): return self.optimal_scale_factor()

  def step_forward(self):
    self.reparametrisation.apply_shifts(self.step())
    self.reparametrisation.linearise()
    self.reparametrisation.store()
    self.taken_step = self.step().deep_copy()

  def step_backward(self):
    self.reparametrisation.apply_shifts(-self.taken_step)
    self.reparametrisation.linearise()
    self.reparametrisation.store()
    self.taken_step = None

  def goof(self):
    return math.sqrt(self.chi_sq_data_only)

  def restrained_goof(self):
    if self.restraints_manager is None:
      return self.goof()
    return math.sqrt(self.chi_sq_data_and_restraints)

  def wR2(self, cutoff_factor=None):
    if cutoff_factor is None:
      return math.sqrt(2*self.objective_data_only)
    fo_sq = self.observations.fo_sq
    strong = fo_sq.data() >= cutoff_factor*fo_sq.sigmas()
    fo_sq = fo_sq.select(strong)
    fc_sq = self.fc_sq.select(strong)
    wght = self.weights.select(strong)
    fc_sq = fc_sq.data()
    fo_sq = fo_sq.data()
    fc_sq *= self.scale_factor()
    wR2 = flex.sum(wght*flex.pow2((fo_sq-fc_sq)))/flex.sum(wght*flex.pow2(fo_sq))
    return math.sqrt(wR2)

  def r1_factor(self, cutoff_factor=None):
    fo_sq = self.observations.fo_sq
    if cutoff_factor is not None:
      strong = fo_sq.data() >= cutoff_factor*fo_sq.sigmas()
      fo_sq = fo_sq.select(strong)
      fc_sq = self.fc_sq.select(strong)
    else:
      fc_sq = self.fc_sq
    f_obs = fo_sq.f_sq_as_f()
    f_calc = fc_sq.f_sq_as_f()
    R1 = f_obs.r1_factor(f_calc,
      scale_factor=math.sqrt(self.scale_factor()), assume_index_matching=True)
    return R1, f_obs.size()

  def covariance_matrix(self,
                        jacobian_transpose=None,
                        normalised_by_goof=True):
    """ The columns of the jacobian_transpose determine which crystallographic
        parameters appear in the covariance matrix.
        If jacobian_transpose is None, then the covariance matrix returned will
        be that for the independent L.S. parameters.
    """
    if not self.step_equations().solved:
      self.solve()
    cov = linalg.inverse_of_u_transpose_u(
      self.step_equations().cholesky_factor_packed_u())
    cov /= self.sum_w_yo_sq()
    if jacobian_transpose is not None:
      cov = jacobian_transpose.self_transpose_times_symmetric_times_self(cov)
    if normalised_by_goof: cov *= self.restrained_goof()**2
    return cov

  def covariance_matrix_and_annotations(self):
    jac_tr = self.reparametrisation.jacobian_transpose_matching_grad_fc()
    return covariance_matrix_and_annotations(
      self.covariance_matrix(jacobian_transpose=jac_tr),
      self.reparametrisation.component_annotations)


class covariance_matrix_and_annotations(object):

  def __init__(self, covariance_matrix, annotations):
    """ The covariance matrix is assumed to be a symmetric matrix stored as a
        packed upper diagonal matrix.
    """
    self.matrix = covariance_matrix
    self.annotations = annotations
    self._2_n_minus_1 = 2*len(self.annotations)-1 # precompute for efficiency

  def __call__(self, i, j):
    return self.matrix[i*(self._2_n_minus_1-i)//2 + j]

  def variance_of(self, annotation):
    i = self.annotations.index(annotation)
    return self(i, i)

  def covariance_of(self, annotation_1, annotation_2):
    i = self.annotations.index(annotation_1)
    j = self.annotations.index(annotation_2)
    if j > i:
      i, j = j, i
    return self(i, j)

  def diagonal(self):
    return self.matrix.matrix_packed_u_diagonal()

from __future__ import division
from xfel.merging.algorithms.error_model.sdfac_refine_lbfgs import sdfac_refinery, sdfac_refine_refltable_lbfgs, lbfgs_minimizer
from xfel.merging.algorithms.error_model.sdfac_propagate import sdfac_propagate, error_terms, r2d
from scitbx.array_family import flex
import math

from xfel.cxi.postrefinement_legacy_rs import unpack_base
class sdfac_propagate_parameterization(unpack_base):
  def __getattr__(YY,item):
    if item=="SDFAC" : return YY.reference[0]
    if item=="SDB"   : return YY.reference[1]
    if item=="SDADD" : return YY.reference[2]
    if item=="SDFACSQ" : return YY.reference[0]**2
    if item=="SDBSQ"   : return YY.reference[1]**2
    if item=="SDADDSQ" : return YY.reference[2]**2
    if item=="sigma_thetax" : return YY.reference[3]
    if item=="sigma_thetay" : return YY.reference[4]
    if item=="sigma_lambda" : return YY.reference[5]
    if item=="sigma_deff"   : return YY.reference[6]
    if item=="sigma_eta"    : return YY.reference[7]
    if item=="sigma_gstar"  : return YY.reference[8:]
    if item=="sd_terms"        : return YY.reference[0:3]
    if item=="propagate_terms" : return YY.reference[3:]
    raise AttributeError(item)

  def show(YY, out):
    print >> out, "sdfac: %20.10f, sdb: %20.10f, sdadd: %20.10f"%(YY.SDFAC, YY.SDB, YY.SDADD)
    for item in "sigma_thetax", "sigma_thetay", "sigma_lambda", "sigma_deff", "sigma_eta":
      if 'theta' in item:
        print >> out, "%s: %20.10f"%(item, r2d(getattr(YY, item))),
      else:
        print >> out, "%s: %20.10f"%(item, getattr(YY, item)),
    print >> out
    for v_id, v in enumerate(YY.sigma_gstar):
      print >> out, "sigma_gstar_%d: %20.10f * 1e-5"%(v_id, v*1e5),
    print >> out

class sdfac_propagate_refinery(sdfac_refinery):
  def __init__(self, scaler, indices, bins, log):
    super(sdfac_propagate_refinery, self).__init__(scaler, indices, bins, log)
    self.propagator = sdfac_propagate(self.scaler, verbose=False)

    # Get derivatives from error propagation
    self.dI_derrorterms = self.propagator.dI_derrorterms()

  def fvec_callable(self, values):
    """ Compute the functional by first propagating errors from postrefinement and then
    applying the current values for the sd parameters to the input data, then computing
    the complete set of normalized deviations and finally using those normalized
    deviations to compute the functional."""

    # Restore original sigmas
    refls = self.ISIGI
    refls['isigi'] = refls['scaled_intensity']/refls['original_sigmas']

    # Propagate errors from postrefinement
    self.propagator.error_terms = error_terms.from_x(values.propagate_terms)
    self.propagator.adjust_errors(dI_derrorterms=self.dI_derrorterms, compute_sums=False)

    # Apply SD terms
    all_sigmas_normalized, _ = self.get_normalized_sigmas(values)

    # Compute functional
    f = flex.double()
    for i, bin in enumerate(self.bins):
      binned_normalized_sigmas = all_sigmas_normalized.select(bin)
      n = len(binned_normalized_sigmas)
      if n == 0:
        f.append(0)
        continue
      # functional is weight * (1-rms(normalized_sigmas))^s summed over all intensitiy bins
      f.append(1-math.sqrt(flex.mean(binned_normalized_sigmas*binned_normalized_sigmas)))

    return f

  def jacobian_callable(self, values):
    # Restore original sigmas
    refls = self.scaler.ISIGI
    refls['isigi'] = refls['scaled_intensity']/refls['original_sigmas']

    # Propagate errors from postrefinement
    self.propagator.error_terms = error_terms.from_x(values.propagate_terms)
    self.propagator.adjust_errors(dI_derrorterms=self.dI_derrorterms, compute_sums=False)

    all_sigmas_normalized, sigma_prime = self.get_normalized_sigmas(values)

    # et: error term
    df_derrorterms = []
    for et, dI_det in zip(values.propagate_terms, self.dI_derrorterms[1:]): # don't need dI wrt iobs
      dsigmasq_det = 2 * et
      dsigmasq_detsq = dI_det**2 * dsigmasq_det
      dsigprimesq_detsq = values.SDFACSQ * dsigmasq_detsq
      df_detsq = self.df_dpsq(all_sigmas_normalized, sigma_prime, dsigprimesq_detsq)
      df_derrorterms.append(df_detsq)

    sdfac_derivatives = super(sdfac_propagate_refinery, self).jacobian_callable(values)

    return sdfac_derivatives + df_derrorterms

class sdfac_propagate_and_refine(sdfac_refine_refltable_lbfgs):
  def __init__(self, scaler):
    sdfac_refine_refltable_lbfgs.__init__(self, scaler)
    self.parameterization = sdfac_propagate_parameterization

  def run_minimzer(self, values, sels, **kwargs):
    refinery = sdfac_propagate_refinery(self.scaler, self.scaler.miller_set.indices(), sels, self.log)
    return lbfgs_minimizer(values.reference, self.parameterization, refinery, self.log,
      show_finite_differences = self.scaler.params.raw_data.error_models.sdfac_refine.show_finite_differences)

  def adjust_errors(self):
    print >> self.log, "Starting adjust_errors"

    # Save original sigmas
    refls = self.scaler.ISIGI
    refls['original_sigmas'] = refls['scaled_intensity']/refls['isigi']

    print >> self.log, "Computing initial estimates of parameters"
    propagator = sdfac_propagate(self.scaler, verbose=False)
    propagator.initial_estimates()
    propagator.adjust_errors(compute_sums=False)
    init_params = flex.double(self.get_initial_sdparams_estimates())
    init_params.extend(propagator.error_terms.to_x())
    values = self.parameterization(init_params)

    print >> self.log, "Initial estimates:",
    values.show(self.log)
    print >> self.log, "Refining error correction parameters"
    sels, binned_intensities = self.get_binned_intensities()
    minimizer = self.run_minimzer(values, sels)
    values = minimizer.get_refined_params()
    print >> self.log, "Final",
    values.show(self.log)

    print >> self.log, "Applying sdfac/sdb/sdadd 1"
    # Restore original sigmas
    refls['isigi'] = refls['scaled_intensity']/refls['original_sigmas']

    # Propagate refined errors from postrefinement
    propagator.error_terms = error_terms.from_x(values.propagate_terms)
    propagator.adjust_errors()
    minimizer.apply_sd_error_params(self.scaler.ISIGI, values)

    self.scaler.summed_weight= flex.double(self.scaler.n_refl, 0.)
    self.scaler.summed_wt_I  = flex.double(self.scaler.n_refl, 0.)

    print >> self.log, "Applying sdfac/sdb/sdadd 2"
    for i in xrange(len(self.scaler.ISIGI)):
      hkl_id = self.scaler.ISIGI['miller_id'][i]
      Intensity = self.scaler.ISIGI['scaled_intensity'][i] # scaled intensity
      sigma = Intensity / self.scaler.ISIGI['isigi'][i] # corrected sigma
      variance = sigma * sigma
      self.scaler.summed_wt_I[hkl_id] += Intensity / variance
      self.scaler.summed_weight[hkl_id] += 1 / variance

    if False:
      # validate using http://ccp4wiki.org/~ccp4wiki/wiki/index.php?title=Symmetry%2C_Scale%2C_Merge#Analysis_of_Standard_Deviations
      print >> self.log, "Validating"
      from matplotlib import pyplot as plt
      all_sigmas_normalized = compute_normalized_deviations(self.scaler.ISIGI, self.scaler.miller_set.indices())
      plt.hist(all_sigmas_normalized, bins=100)
      plt.figure()

      binned_rms_normalized_sigmas = []

      for i, sel in enumerate(sels):
        binned_rms_normalized_sigmas.append(math.sqrt(flex.mean(all_sigmas_normalized.select(sel)*all_sigmas_normalized.select(sel))))

      plt.plot(binned_intensities, binned_rms_normalized_sigmas, 'o')
      plt.show()

      all_sigmas_normalized = all_sigmas_normalized.select(all_sigmas_normalized != 0)
      self.normal_probability_plot(all_sigmas_normalized, (-0.5, 0.5), plot = True)

class sdfac_propagate_and_refine_levmar(sdfac_propagate_and_refine):
  def run_minimzer(self, values, sels, **kwargs):
    from xfel.merging.algorithms.error_model.sdfac_refine_levmar import sdfac_helper
    from scitbx.lstbx import normal_eqns_solving

    self.refinery = sdfac_propagate_refinery(self.scaler, self.scaler.miller_set.indices(), sels, self.log)
    self.helper = sdfac_helper(current_x = values.reference,
                               parameterization = self.parameterization, refinery = self.refinery,
                               out = self.log )
    self.iterations = normal_eqns_solving.levenberg_marquardt_iterations(
      non_linear_ls = self.helper,
      track_all=True,
      gradient_threshold=1e-08,
      step_threshold=1e-08,
      tau=1e-08,
      n_max_iterations=200)
    return self

  def get_refined_params(self):
    return self.parameterization(self.helper.x)

  def apply_sd_error_params(self, data, values):
    self.refinery.apply_sd_error_params(data, values)

import cctbx.sgtbx

from scitbx.python_utils import misc
ext = misc.import_ext("cctbx_boost.miller_ext")
misc.import_regular_symbols(globals(), ext.__dict__)
del misc

from cctbx import crystal
from cctbx import maptbx
from cctbx import uctbx
from cctbx.array_family import flex
from scitbx import fftpack
import sys
import math

class binner(ext.binner):

  def __init__(self, binning, miller_indices):
    ext.binner.__init__(self, binning, miller_indices)

  def show_summary(self, f=sys.stdout):
    for i_bin in self.range_all():
      bin_d_range = self.bin_d_range(i_bin)
      count = self.count(i_bin)
      if (i_bin == self.i_bin_d_too_large()):
        assert bin_d_range[0] == -1
        print >> f, "unused:              d > %8.4f: %5d" % (
          bin_d_range[1], count)
      elif (i_bin == self.i_bin_d_too_small()):
        assert bin_d_range[1] == -1
        print >> f, "unused: %9.4f >  d           : %5d" % (
          bin_d_range[0], count)
      else:
        print >> f, "bin %2d: %9.4f >= d > %8.4f: %5d" % (
          (i_bin,) + bin_d_range + (count,))

def make_lookup_dict(indices): # XXX push to C++
  result = {}
  for i in xrange(len(indices)):
    result[indices[i]] = i
  return result

class set(crystal.symmetry):

  def __init__(self, crystal_symmetry, indices, anomalous_flag=None):
    assert anomalous_flag in (None, False, True)
    crystal.symmetry._copy_constructor(self, crystal_symmetry)
    self._indices = indices
    self._anomalous_flag = anomalous_flag

  def _copy_constructor(self, other):
    crystal.symmetry._copy_constructor(self, other)
    self._indices = other._indices
    self._anomalous_flag = other._anomalous_flag

  def indices(self):
    return self._indices

  def anomalous_flag(self):
    return self._anomalous_flag

  def show_summary(self, f=sys.stdout):
    print >> f, "Number of Miller indices:", len(self.indices())
    print >> f, "Anomalous flag:", self.anomalous_flag()
    crystal.symmetry.show_summary(self, f)
    return self

  def multiplicities(self):
    return array(
      self,
      self.space_group().multiplicity(self.indices(), self.anomalous_flag()))

  def epsilons(self):
    return array(
      self,
      self.space_group().epsilon(self.indices()))

  def d_spacings(self):
    return array(
      self, self.unit_cell().d(self.indices()))

  def sin_theta_over_lambda_sq(self):
    return array(
      self, self.unit_cell().stol_sq(self.indices()))

  def d_min(self):
    return uctbx.d_star_sq_as_d(self.unit_cell().max_d_star_sq(self.indices()))

  def resolution_range(self):
    r = self.unit_cell().min_max_d_star_sq(self.indices())
    return tuple([uctbx.d_star_sq_as_d(x) for x in r])

  def change_basis(self, cb_op):
    return set(
      crystal_symmetry=crystal.symmetry.change_basis(self, cb_op),
      indices=cb_op.apply(self.indices()),
      anomalous_flag=self.anomalous_flag())

  def expand_to_p1(self):
    assert self.space_group() != None
    assert self.indices() != None
    assert self.anomalous_flag() != None
    p1 = expand_to_p1(
      self.space_group(), self.anomalous_flag(), self.indices())
    return set(self.cell_equivalent_p1(), p1.indices(), self.anomalous_flag())

  def setup_binner(self, d_max=0, d_min=0,
                   auto_binning=0,
                   reflections_per_bin=0,
                   n_bins=0):
    assert auto_binning != 0 or reflections_per_bin != 0 or n_bins != 0
    assert auto_binning != 0 or (reflections_per_bin == 0 or n_bins == 0)
    if (auto_binning):
      if (reflections_per_bin == 0): reflections_per_bin = 200
      if (n_bins == 0): n_bins = 8
      n_per_bin = int(float(len(self.indices())) / n_bins + .5)
      if (n_per_bin > reflections_per_bin):
        n_bins = int(len(self.indices()) / reflections_per_bin + .5)
    elif (reflections_per_bin):
      n_bins = int(len(self.indices()) / reflections_per_bin + .5)
    assert n_bins > 0
    assert self.unit_cell() != None
    bng = binning(self.unit_cell(), n_bins, self.indices(), d_max, d_min)
    self._binner = binner(bng, self.indices())
    return self.binner()

  def binner(self):
    return self._binner

  def use_binner_of(self, other):
    self._binner = other._binner

def build_set(crystal_symmetry, anomalous_flag, d_min):
  return set(
    crystal_symmetry,
    index_generator(
      crystal_symmetry.unit_cell(),
      crystal_symmetry.space_group_info().type(),
      anomalous_flag,
      d_min).to_array(),
    anomalous_flag)

def _ftor_a_s_sub(lhs, rhs): return lhs - rhs
def _ftor_a_s_div(lhs, rhs): return lhs / rhs

def _array_info(array):
  if (array == None): return str(None)
  try:
    return array.__class__.__name__ + ", size=%d" % (len(array),)
  except:
    return "Unknown"

class array(set):

  def __init__(self, miller_set, data=None, sigmas=None, info=None):
    set._copy_constructor(self, miller_set)
    self._data = data
    self._sigmas = sigmas
    self._info = info

  def _copy_constructor(self, other):
    set._copy_constructor(self, other)
    self._data = other._data
    self._sigmas = other._sigmas
    self._info = other._info

  def data(self):
    return self._data

  def sigmas(self):
    return self._sigmas

  def info(self):
    return self._info

  def show_summary(self, f=sys.stdout):
    print >> f, "Miller array info:", self.info()
    print >> f, "Type of data:", _array_info(self.data())
    print >> f, "Type of sigmas:", _array_info(self.sigmas())
    set.show_summary(self, f)
    return self

  def set_info(self, info):
    self._info = info

  def f_sq_as_f(self, tolerance=1.e-6):
    from cctbx import xray
    if (self.sigmas() != None):
      r = xray.array_f_sq_as_f(self.data(), self.sigmas(), tolerance)
      return array(self, r.f, r.sigma_f)
    return array(self, xray.array_f_sq_as_f(self.data()).f)

  def f_as_f_sq(self):
    from cctbx import xray
    if (self.sigmas() != None):
      r = xray.array_f_as_f_sq(self.data(), self.sigmas())
      return array(self, r.f_sq, r.sigma_f_sq)
    return array(self, xray.array_f_as_f_sq(self.data()).f_sq)

  def map_to_asu(self):
    i = self.indices().deep_copy()
    d = self.data().deep_copy()
    map_to_asu(
      self.space_group_info().type(),
      self.anomalous_flag(),
      i, d)
    return array(set(self, i, self.anomalous_flag()), d, self.sigmas())

  def change_basis(self, cb_op):
    new_data = None
    new_sigmas = None
    if (self.data() != None):
      assert type(self.data()) == type(flex.double())
      new_data = self.data().deep_copy()
    if (self.sigmas() != None):
      assert type(self.sigmas()) == type(flex.double())
      new_sigmas = self.sigmas().deep_copy()
    return array(
      miller_set=set.change_basis(self, cb_op),
      data=new_data,
      sigmas=new_sigmas)

  def anomalous_differences(self):
    assert self.anomalous_flag() == True
    assert self.indices() != None
    assert self.data() != None
    if (self.space_group() != None):
      asu = self.map_to_asu()
      matching = match_bijvoet_mates(
        asu.space_group_info().type(), asu.indices())
      d = asu.data()
    else:
      matching = match_bijvoet_mates(self.indices())
      d = self.data()
    i = matching.miller_indices_in_hemisphere("+")
    d = matching.minus(d)
    s = None
    if (self.sigmas() != None):
      s = matching.additive_sigmas(self.sigmas())
    return array(set(self, i, anomalous_flag=False), d, s)

  def all_selection(self):
    return flex.bool(self.indices().size(), True)

  def apply_selection(self, flags, negate=False):
    assert self.indices() != None
    if (negate): flags = ~flags
    i = self.indices().select(flags)
    d = None
    if (self.data() != None): d = self.data().select(flags)
    s = None
    if (self.sigmas() != None): s = self.sigmas().select(flags)
    return array(set(self, i, self.anomalous_flag()), d, s)

  def resolution_filter(self, d_max=0, d_min=0, negate=0):
    d = self.d_spacings().data()
    keep = self.all_selection()
    if (d_max): keep &= d <= d_max
    if (d_min): keep &= d >= d_min
    return self.apply_selection(keep, negate)

  def sigma_filter(self, cutoff_factor, negate=0):
    assert self.data() != None
    assert self.sigmas() != None
    flags = flex.abs(self.data()) >= self.sigmas() * cutoff_factor
    return self.apply_selection(flags, negate)

  def _generic_binner_action(self, use_binning, use_multiplicities,
                             function,
                             function_weighted):
    assert self.indices() != None
    assert self.data() != None
    if (use_multiplicities):
      mult = self.multiplicities().data().as_double()
    if (not use_binning):
      if (not use_multiplicities):
        result = function(self.data())
      else:
        result = function_weighted(self.data(), mult)
    else:
      result = flex.double()
      for i_bin in self.binner().range_used():
        sel = self.binner().selection(i_bin)
        if (sel.count(1) == 0):
          result.append(0)
        else:
          sel_data = self.data().select(sel)
          if (not use_multiplicities):
            result.append(function(sel_data))
          else:
            sel_mult = mult.select(sel)
            result.append(function_weighted(sel_data, sel_mult))
    return result

  def mean(self, use_binning=0, use_multiplicities=0):
    return self._generic_binner_action(use_binning, use_multiplicities,
      flex.mean,
      flex.mean_weighted)

  def mean_sq(self, use_binning=0, use_multiplicities=0):
    return self._generic_binner_action(use_binning, use_multiplicities,
      flex.mean_sq,
      flex.mean_sq_weighted)

  def rms(self, use_binning=0, use_multiplicities=0):
    ms = self.mean_sq(use_binning, use_multiplicities)
    if (not use_binning):
      return math.sqrt(ms)
    else:
      return flex.sqrt(ms)

  def rms_filter(self, cutoff_factor,
                 use_binning=0, use_multiplicities=0, negate=0):
    rms = self.rms(use_binning, use_multiplicities)
    abs_data = flex.abs(self.data())
    if (not use_binning):
      keep = abs_data <= cutoff_factor * rms
    else:
      keep = self.all_selection()
      for i_bin in self.binner().range_used():
        keep &= ~self.binner().selection(i_bin) \
             | (abs_data <= cutoff_factor * rms[i_bin-1])
    return self.apply_selection(keep, negate)

  def statistical_mean(self, use_binning=0):
    if (not use_binning):
      result = statistical_mean(
        self.space_group(), self.anomalous_flag(), self.indices(), self.data())
    else:
      result = flex.double()
      for i_bin in self.binner().range_used():
        sel = self.binner().selection(i_bin)
        if (sel.count(1) == 0):
          result.append(0)
        else:
          result.append(statistical_mean(
            self.space_group(), self.anomalous_flag(),
            self.indices().select(sel),
            self.data().select(sel)))
    return result

  def _generic_binner_application(self, binned_values, ftor, result_data):
    result_perm = flex.size_t()
    for i_bin in self.binner().range_used():
      result_perm.append(self.binner().array_indices(i_bin))
      result_data.append(
        ftor(self.data().select(self.binner().selection(i_bin)),
             binned_values[i_bin-1]))
    return array(self, result_data.shuffle(result_perm))

  def remove_patterson_origin_peak(self):
    s_mean = self.statistical_mean(use_binning=1)
    result_data = flex.double()
    return self._generic_binner_application(s_mean, _ftor_a_s_sub, result_data)

  def normalize_structure_factors(self):
    mean = self.mean(use_binning=1, use_multiplicities=1)
    result_data = flex.double()
    return self._generic_binner_application(mean, _ftor_a_s_div, result_data)

  def __abs__(self):
    return array(self, flex.abs(self.data()), self.sigmas())

  def __add__(self, other):
    assert self.indices() != None
    assert self.data() != None
    if (type(other) != type(self)):
      # add a scalar
      return array(self, self.data() + other)
    # add arrays
    assert other.indices() != None
    assert other.data() != None
    match = match_indices(self.indices(), other.indices())
    i = match.paired_miller_indices(0)
    d = match.plus(self.data(), other.data())
    s = None
    if (self.sigmas() != None and other.sigmas() != None):
      s = match.additive_sigmas(self.sigmas(), other.sigmas())
    return array(set(self, i), d, s)

  def show_array(self, f=sys.stdout):
    assert self.data().size() == self.indices().size()
    if (self.sigmas() == None):
      for i,h in self.indices().items():
        print >> f, h, self.data()[i]
    else:
      assert self.indices().size() == self.sigmas().size()
      for i,h in self.indices().items():
        print >> f, h, self.data()[i], self.sigmas()[i]
    return self

class fft_map(crystal.symmetry):

  def __init__(self, coeff_array,
                     grid_resolution_factor=1./3,
                     max_prime=5):
    assert coeff_array.anomalous_flag() in (False, True)
    crystal.symmetry._copy_constructor(self, coeff_array)
    self._grid_resolution_factor = grid_resolution_factor
    self._max_prime = max_prime
    self._anomalous_flag = coeff_array.anomalous_flag()
    cf = coeff_array.data()
    if (cf.size() == 0):
      cf = flex.complex_double()
    elif (type(cf[0]) != type(0j)):
      ph = flex.double(cf.size(), 0)
      cf = flex.polar(cf, ph)
      del ph
    n_real = maptbx.determine_grid(
      unit_cell=coeff_array.unit_cell(),
      d_min=coeff_array.d_min(),
      resolution_factor=grid_resolution_factor,
      max_prime=self.max_prime(),
      mandatory_factors=coeff_array.space_group().gridding())
    if (not self.anomalous_flag()):
      rfft = fftpack.real_to_complex_3d(n_real)
      n_complex = rfft.n_complex()
    else:
      cfft = fftpack.complex_to_complex_3d(n_real)
      n_complex = cfft.n()
    conjugate_flag = False # XXX correct?
    map = maptbx.structure_factors.to_map(
      self.space_group(),
      self.anomalous_flag(),
      coeff_array.indices(),
      cf,
      flex.grid(n_complex),
      conjugate_flag)
    if (not self.anomalous_flag()):
      self._real_map = rfft.backward(map.complex_map())
    else:
      self._complex_map = cfft.backward(map.complex_map())

  def grid_resolution_factor(self):
    return self._grid_resolution_factor

  def max_prime(self):
    return self._max_prime

  def anomalous_flag(self):
    return self._anomalous_flag

  def real_map(self):
    if (not self.anomalous_flag()):
      return self._real_map
    else:
      return flex.real(self._complex_map)

  def complex_map(self):
    assert self.anomalous_flag()
    return self._complex_map

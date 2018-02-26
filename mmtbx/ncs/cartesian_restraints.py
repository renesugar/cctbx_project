from __future__ import division
from scitbx.array_family import flex

import boost.python
ext = boost.python.import_ext("mmtbx_ncs_cartesian_restraints_ext")
from mmtbx_ncs_cartesian_restraints_ext import *

from cctbx import adptbx
import scitbx.restraints
from scitbx.math import superpose
from scitbx import matrix
from libtbx.str_utils import show_string
from libtbx.utils import Sorry
from libtbx import adopt_init_args
from itertools import count
import sys
from libtbx.str_utils import line_breaker
from mmtbx.ncs.ncs_params import global_ncs_params

class cartesian_ncs_manager(object):
  def __init__(self, model, ncs_params, ext_groups=None):
    # create bunch of group objects
    self.ncs_params = ncs_params
    if self.ncs_params is None:
      self.ncs_params = global_ncs_params.extract().ncs
    if ext_groups is not None:
      self.groups_list = ext_groups
    else:
      self.groups_list = []
      ncs_obj = model.get_ncs_obj()
      ncs_restraints_group_list = ncs_obj.get_ncs_restraints_group_list()
      ncs_groups_selection_string_list = ncs_restraints_group_list.get_array_of_str_selections()
      for i_gr, gr in enumerate(ncs_restraints_group_list):
        n_copies = gr.get_number_of_copies()
        registry = pair_registry(n_seq=model.get_number_of_atoms(), n_ncs=n_copies+1)
        for i_copy, c in enumerate(gr.copies):
          for i_seq, j_seq in zip(gr.master_iselection, c.iselection):
            stat, i_diag = registry.enter(
                i_seq=i_seq, j_seq=j_seq, j_ncs=i_copy+1)
        for i_pair,pair in enumerate(registry.selection_pairs()):
          if (pair[0].size() < 2):
            detail = ["do not produce any pairs",
                      "produce only one pair"][pair[0].size()]
            raise Sorry("\n".join([
              "NCS restraints selections %s of matching atoms:" % detail,
              "  Reference selection: %s" % show_string(self.selection_strings[0]),
              "      Other selection: %s" % show_string(
                self.selection_strings[i_pair+1])]))
        g = _group(selection_strings=ncs_groups_selection_string_list[i_gr],
            registry=registry,
            u_average_min=1.e-6,)
        self.groups_list.append(g)

  def select(self, iselection):
    ext_groups = []
    for group in self.groups_list:
      ext_groups.append(group.select(iselection))
    return cartesian_ncs_manager(
        model=None,
        ncs_params=self.ncs_params,
        ext_groups=ext_groups)

  def energies_adp_iso(self,
        u_isos,
        average_power,
        compute_gradients=True,
        gradients=None,
        normalization=False):
    result = scitbx.restraints.energies(
      compute_gradients=compute_gradients,
      gradients=gradients,
      gradients_size=u_isos.size(),
      gradients_factory=flex.double,
      normalization=normalization)
    result.rms_with_respect_to_averages = []
    if (self.ncs_params.b_factor_weight is None
        or self.ncs_params.b_factor_weight <= 0):
      result.rms_with_respect_to_averages = [None]*len(self.groups_list)
    else:
      for group in self.groups_list:
        contribution = group.energies_adp_iso(
            u_isos=u_isos,
            b_factor_weight=self.ncs_params.b_factor_weight,
            average_power=average_power,
            compute_gradients=compute_gradients,
            gradients=result.gradients)
        result += contribution
        result.rms_with_respect_to_averages.append(
            contribution.rms_with_respect_to_average)
    result.finalize_target_and_gradients()
    return result

  def show_adp_iso_differences_to_average(self,
         u_isos,
         site_labels,
         out=None,
         prefix=""):
    if (self.ncs_params.b_factor_weight is None
        or self.ncs_params.b_factor_weight <= 0):
      print >> out, \
        prefix+"  b_factor_weight: %s  =>  restraints disabled" % (
          str(self.ncs_params.b_factor_weight))
    for i_group,group in enumerate(self.groups_list):
      print >> out, prefix + "NCS restraint group %d:" % (i_group+1)
      energies_adp_iso = group.energies_adp_iso(
        u_isos=u_isos,
        b_factor_weight=self.ncs_params.b_factor_weight,
        average_power=1,
        compute_gradients=False)
      print >> out, prefix + "  weight: %.6g" % energies_adp_iso.weight
      energies_adp_iso.show_differences_to_average(
        site_labels=site_labels, out=out, prefix=prefix+"  ")

  def get_n_groups(self):
    return len(self.groups_list)

  def register_additional_isolated_sites(self, number):
    for group in self.groups_list:
      group.register_additional_isolated_sites(number=number)

  def compute_operators(self, sites_cart):
    for group in self.groups_list:
      group.compute_operators(sites_cart=sites_cart)

  def energies_sites(self,
        sites_cart,
        compute_gradients=True,
        gradients=None,
        normalization=False):
    self.compute_operators(sites_cart=sites_cart)
    result = scitbx.restraints.energies(
      compute_gradients=compute_gradients,
      gradients=gradients,
      gradients_size=sites_cart.size(),
      gradients_factory=flex.vec3_double,
      normalization=normalization)
    result.rms_with_respect_to_averages = []
    if (self.ncs_params.coordinate_sigma is None
        or self.ncs_params.coordinate_sigma <= 0):
      result.rms_with_respect_to_averages = [None]*len(self.groups_list)
    else:
      for group in self.groups_list:
        contribution = group.energies_sites(
            sites_cart=sites_cart,
            coordinate_sigma = self.ncs_params.coordinate_sigma,
            compute_gradients=compute_gradients,
            gradients=result.gradients)
        result += contribution
        result.rms_with_respect_to_averages.append(
            contribution.rms_with_respect_to_average)
    result.finalize_target_and_gradients()
    return result

  def show_operators(self, sites_cart, out=None, prefix=""):
    for i_group,group in enumerate(self.groups_list):
      print >> out, prefix + "NCS restraint group %d:" % (i_group+1)
      group.show_operators(sites_cart=sites_cart, out=out, prefix=prefix+"  ")

  def as_pdb(self, sites_cart, out):
    result = out
    pr = "REMARK   3  "
    print >> result, pr+"NCS DETAILS."
    print >> result, pr+" NUMBER OF NCS GROUPS : %-6d" % self.get_n_groups()
    for i_group, group in enumerate(self.groups_list):
      print >>result,pr+" NCS GROUP : %-6d"%(i_group+1)
      selection_strings = group.selection_strings
      for i_op,pair,mx,rms in zip(
          count(1),
          group.selection_pairs,
          group.matrices,
          group.rms):
        print >> result,pr+"  NCS OPERATOR : %-d" % i_op
        lines = line_breaker(selection_strings[0], width=34)
        for i_line, line in enumerate(lines):
          if(i_line == 0):
            print >> result, pr+"   REFERENCE SELECTION: %s"%line
          else:
            print >> result, pr+"                      : %s"%line
        lines = line_breaker(selection_strings[i_op], width=34)
        for i_line, line in enumerate(lines):
          if(i_line == 0):
            print >> result, pr+"   SELECTION          : %s"%line
          else:
            print >> result, pr+"                      : %s"%line
        print >> result,pr+"   ATOM PAIRS NUMBER  : %-d" % len(pair[0])
        print >> result,pr+"   RMSD               : %-10.3f" % rms
    return result.getvalue()

  def as_cif_block(self, loops, cif_block, sites_cart):
    if cif_block is None:
      cif_block = iotbx.cif.model.block()
    (ncs_ens_loop, ncs_dom_loop, ncs_dom_lim_loop, ncs_oper_loop,
        ncs_ens_gen_loop) = loops

    oper_id = 0
    if self.get_n_groups > 0:
      for i_group, group in enumerate(self.groups_list):
        ncs_ens_loop.add_row((i_group+1, "?"))
        selection_strings = group.selection_strings
        matrices = group.matrices
        rms = group.rms
        pair_count = len(group.selection_pairs[0])
        for i_domain, domain_selection in enumerate(selection_strings):
          ncs_dom_loop.add_row((i_domain+1, i_group+1, "?"))
          # XXX TODO: export individual sequence ranges from selection
          ncs_dom_lim_loop.add_row(
            (i_group+1, i_domain+1, "?", "?", "?", "?", domain_selection))
          if i_domain > 0:
            rt_mx = group.matrices[i_domain-1]
            oper_id += 1
            row = [oper_id, "given"]
            row.extend(rt_mx.r)
            row.extend(rt_mx.t)
            row.append("?")
            ncs_oper_loop.add_row(row)
            ncs_ens_gen_loop.add_row((1, i_domain+1, i_group+1, oper_id))
    cif_block.add_loop(ncs_ens_loop)
    cif_block.add_loop(ncs_dom_loop)
    cif_block.add_loop(ncs_dom_lim_loop)
    if self.get_n_groups > 0:
      cif_block.add_loop(ncs_oper_loop)
      cif_block.add_loop(ncs_ens_gen_loop)
    return cif_block

  def show_sites_distances_to_average(self,
         sites_cart,
         site_labels,
         excessive_distance_limit=None,
         out=None,
         prefix=""):
    self.compute_operators(sites_cart)
    n_excessive = 0
    if (self.ncs_params.coordinate_sigma is None or
        self.ncs_params.coordinate_sigma <= 0):
      print >> out, \
        prefix+"  coordinate_sigma: %s  =>  restraints disabled" % (
          str(self.ncs_params.coordinate_sigma))
      return n_excessive
    for i_group,group in enumerate(self.groups_list):
      print >> out, prefix + "NCS restraint group %d:" % (i_group+1)
      print >> out, prefix + "  coordinate_sigma: %.6g" % (
        self.ncs_params.coordinate_sigma)
      energies_sites = group.energies_sites(
        sites_cart=sites_cart,
        coordinate_sigma = self.ncs_params.coordinate_sigma,
        compute_gradients=False)
      print >> out, prefix + "  weight:  %.6g" % energies_sites.weight
      n_excessive += energies_sites.show_distances_to_average(
        site_labels=site_labels,
        excessive_distance_limit=excessive_distance_limit,
        out=out,
        prefix=prefix+"  ")
      print n_excessive
    return n_excessive

  def selection_restrained(self, n_seq=None):
    if (n_seq is None):
      n_seq = -1
      for group in self.groups_list:
        for pair in group.selection_pairs:
          for sel in pair:
            n_seq = max(n_seq, flex.max(sel))
      n_seq += 1
    result = flex.bool(n_seq, False)
    for group in self.groups_list:
      for pair in group.selection_pairs:
        for sel in pair:
          result.set_selected(sel, True)
    return result

class _group(object):
  """
  DO NOT USE THIS CLASS ANYWERE ELSE.
  This class is exclusively used in cartesian NCS restraints.
  It is being created by cartesian_ncs_manager here and not used anywhere
  outside this file.
  """
  def __init__(self,
        selection_strings,
        registry,
        u_average_min):
      adopt_init_args(self, locals())
      self.selection_pairs = registry.selection_pairs()
      self.matrices = []
      self.rms = []

  def register_additional_isolated_sites(self, number):
    self.registry.register_additional_isolated_sites(number=number)

  def select(self, iselection):
    if(not isinstance(iselection, flex.size_t)):
      iselection = iselection.iselection()
    return _group(
      selection_strings=self.selection_strings,
      registry=self.registry.proxy_select(iselection=iselection),
      u_average_min=self.u_average_min)

  def compute_operators(self, sites_cart):
    for pair in self.selection_pairs:
      superposition = superpose.least_squares_fit(
        reference_sites=sites_cart.select(pair[0]),
        other_sites=sites_cart.select(pair[1]))
      rtmx = matrix.rt((superposition.r, superposition.t))
      self.matrices.append(rtmx)
      x = sites_cart.select(pair[0])
      y = rtmx * sites_cart.select(pair[1])
      d_sq = (x-y).dot()
      self.rms.append(flex.mean(d_sq)**0.5)

  def show_operators(self,
      sites_cart,
      n_slots_difference_histogram=6,
      out=None,
      prefix=""):
    self.compute_operators(sites_cart)
    if (out is None): out = sys.stdout
    # selection_strings = self.group.selection_strings
    for i_op,pair,mx,rms in zip(
          count(1),
          self.selection_pairs,
          self.matrices,
          self.rms):
      print >> out, prefix + "NCS operator %d:" % i_op
      print >> out, prefix + "  Reference selection:", \
        show_string(self.selection_strings[0])
      print >> out, prefix + "      Other selection:", \
        show_string(self.selection_strings[i_op])
      print >> out, prefix + "  Number of atom pairs:", len(pair[0])
      print >> out, mx.r.mathematica_form(
        label="Rotation", format="%.6g", one_row_per_line=True,
        prefix=prefix+"  ")
      print >> out, mx.t.mathematica_form(
        label="Translation", format="%.6g", prefix=prefix+"  ")
      x = sites_cart.select(pair[0])
      y = mx * sites_cart.select(pair[1])
      d_sq = (x-y).dot()
      if (n_slots_difference_histogram is not None):
        print >> out, prefix + "  Histogram of differences:"
        diff_histogram = flex.histogram(
          data=flex.sqrt(d_sq), n_slots=n_slots_difference_histogram)
        diff_histogram.show(
          f=out, prefix=prefix+"    ", format_cutoffs="%8.6f")
      print >> out, \
        prefix + "  RMS difference with respect to the reference: %8.6f" %(rms)

  def energies_adp_iso(self,
        u_isos,
        b_factor_weight,
        average_power,
        compute_gradients=True,
        gradients=None):
    return _energies_adp_iso(
      group=self,
      u_isos=u_isos,
      b_factor_weight=b_factor_weight,
      average_power=average_power,
      compute_gradients=compute_gradients,
      gradients=gradients)

  def energies_sites(self,
        sites_cart,
        coordinate_sigma,
        compute_gradients=True,
        gradients=None,
        sites_average=None):
    return _energies_sites(
      group=self,
      sites_cart=sites_cart,
      coordinate_sigma=coordinate_sigma,
      compute_gradients=compute_gradients,
      gradients=gradients,
      sites_average=sites_average)

class _energies_adp_iso(scitbx.restraints.energies):

  def __init__(self,
        group,
        u_isos,
        b_factor_weight,
        average_power,
        compute_gradients,
        gradients):
    scitbx.restraints.energies.__init__(self,
      compute_gradients=compute_gradients,
      gradients=gradients,
      gradients_size=u_isos.size(),
      gradients_factory=flex.double,
      normalization=False)
    self.group = group
    self.u_isos = u_isos
    self.average_power = average_power
    # XXX registry should be condensed to map of std::vectors
    #     then all the code below and adp_iso_residual_sum could
    #     become a method of the reduced registry
    max_index = 0
    for pair in self.group.selection_pairs:
      max_index = max(max_index, pair[0][-1])
    u_isos_sum = flex.double(max_index+1, 0)
    u_isos_count = flex.size_t(max_index+1, 0)
    for pair in self.group.selection_pairs:
      u_isos_sum.set_selected(pair[0], u_isos.select(pair[0]))
      u_isos_count.set_selected(pair[0], 1)
    for pair in self.group.selection_pairs:
      u_isos_sum.add_selected(pair[0], u_isos.select(pair[1]))
      u_isos_count.set_selected(pair[0], u_isos_count.select(pair[0])+1)
    sel = u_isos_count == 0
    u_isos_count.set_selected(sel, 1)
    u_isos_average = u_isos_sum / u_isos_count.as_double()
    u_isos_count.set_selected(sel, 0)
    sel = (~sel).iselection()
    self.rms_with_respect_to_average = flex.double()
    def residual_contribution(u_isos_current, u_isos_average):
      diff = u_isos_current - u_isos_average
      self.rms_with_respect_to_average.append(adptbx.u_as_b(
        flex.mean_sq(diff)**0.5))
      self.number_of_restraints += diff.size()
    residual_contribution(
      u_isos_current=u_isos.select(sel),
      u_isos_average=u_isos_average.select(sel))
    for pair in self.group.selection_pairs:
      residual_contribution(
        u_isos_current=u_isos.select(pair[1]),
        u_isos_average=u_isos_average.select(pair[0]))
    self.weight = b_factor_weight
    self.residual_sum = self.group.registry.adp_iso_residual_sum(
      weight=self.weight,
      average_power=self.average_power,
      u_isos=u_isos,
      u_average_min=self.group.u_average_min,
      gradients=self.gradients)
    self.finalize_target_and_gradients()
    self.u_isos_count = u_isos_count
    self.u_isos_average = u_isos_average

  def show_differences_to_average(self, site_labels, out=None, prefix=""):
    if (out is None): out = sys.stdout
    assert len(site_labels) == self.u_isos.size()
    max_label_size = 1
    for label in site_labels:
      max_label_size = max(max_label_size, len(label))
    fmt = "  %%%ds: %%7.2f - %%7.2f = %%8.4f" % max_label_size
    def show_selection(i_ncs, pair):
      print >> out, prefix + "NCS selection:", \
        show_string(self.group.selection_strings[i_ncs])
      print >> out, prefix + " "*(max_label_size+2) \
        + "    B-iso   NCS ave  Difference"
      u_isos_current = self.u_isos.select(pair[1])
      u_isos_average = self.u_isos_average.select(pair[0])
      for i,c,a in zip(pair[1], u_isos_current, u_isos_average):
        c = adptbx.u_as_b(c)
        a = adptbx.u_as_b(a)
        print >> out, prefix + fmt % (site_labels[i], c, a, c-a)
    sel = (self.u_isos_count != 0).iselection()
    show_selection(i_ncs=0, pair=[sel, sel])
    for i_ncs,pair in zip(count(1), self.group.selection_pairs):
      show_selection(i_ncs=i_ncs, pair=pair)


class _energies_sites(scitbx.restraints.energies):

  def __init__(self,
        group,
        sites_cart,
        coordinate_sigma,
        compute_gradients,
        gradients,
        sites_average):
    scitbx.restraints.energies.__init__(self,
      compute_gradients=compute_gradients,
      gradients=gradients,
      gradients_size=sites_cart.size(),
      gradients_factory=flex.vec3_double,
      normalization=False)
    self.group = group
    self.sites_cart = sites_cart
    selection_pairs = self.group.selection_pairs
    max_index = 0
    for pair in selection_pairs:
      max_index = max(max_index, pair[0][-1])
    sites_sum = flex.vec3_double(max_index+1, (0,0,0))
    sites_count = flex.size_t(max_index+1, 0)
    for pair in selection_pairs:
      sites_sum.set_selected(pair[0], sites_cart.select(pair[0]))
      sites_count.set_selected(pair[0], 1)
    for pair,op in zip(selection_pairs, self.group.matrices):
      sites_sum.add_selected(pair[0], op*sites_cart.select(pair[1]))
      sites_count.set_selected(pair[0], sites_count.select(pair[0])+1)
    sel = sites_count == 0
    sites_count.set_selected(sel, 1)
    if (sites_average is not None):
      assert sites_average.size() == sites_count.size()
    else:
      sites_average = sites_sum / sites_count.as_double()
    sites_count.set_selected(sel, 0)
    sel = (~sel).iselection()
    assert coordinate_sigma > 0
    self.weight = 1/coordinate_sigma**2
    self.rms_with_respect_to_average = flex.double()
    if (self.gradients is not None):
      self.gradients.add_selected(
        sel,
        self.residual_contribution(
          sites_current=sites_cart.select(sel),
          sites_average=sites_average.select(sel)))
      for pair,op in zip(selection_pairs, self.group.matrices):
        self.gradients.add_selected(
          pair[1],
          self.residual_contribution(
            sites_current=sites_cart.select(pair[1]),
            sites_average=op.inverse() * sites_average.select(pair[0])))
    else:
      self.residual_contribution(
        sites_current=sites_cart.select(sel),
        sites_average=sites_average.select(sel))
      for pair,op in zip(selection_pairs, self.group.matrices):
        self.residual_contribution(
          sites_current=sites_cart.select(pair[1]),
          sites_average=op.inverse() * sites_average.select(pair[0]))
    self.finalize_target_and_gradients()
    self.sites_count = sites_count
    self.sites_average = sites_average

  def residual_contribution(self, sites_current, sites_average):
    diff = sites_current - sites_average
    self.rms_with_respect_to_average.append(flex.mean(diff.dot())**0.5)
    self.number_of_restraints += diff.size()
    self.residual_sum += self.weight * diff.sum_sq()
    if (self.gradients is not None):
      return (2 * self.weight) * diff

  def show_distances_to_average(self,
        site_labels,
        excessive_distance_limit=None,
        out=None,
        prefix=""):
    if (out is None): out = sys.stdout
    assert len(site_labels) == self.sites_cart.size()
    max_label_size = 1
    for label in site_labels:
      max_label_size = max(max_label_size, len(label))
    fmt = "  %%%ds: %%8.4f" % max_label_size
    def show_selection(i_ncs, pair, op):
      print >> out, prefix + "NCS selection:", \
        show_string(self.group.selection_strings[i_ncs])
      print >> out, prefix + " "*(max_label_size+2) \
        + "  Distance to NCS average"
      sites_current = self.sites_cart.select(pair[1])
      if (op is None):
        sites_average = self.sites_average.select(pair[0])
      else:
        sites_average = op.inverse() * self.sites_average.select(pair[0])
      n_excessive = 0
      for i,c,a in zip(pair[1], sites_current, sites_average):
        abs_diff = abs(matrix.col(c) - matrix.col(a))
        print >> out, prefix + fmt % (site_labels[i], abs_diff),
        if (excessive_distance_limit is not None
            and abs_diff >= excessive_distance_limit):
          print >> out, "EXCESSIVE",
          n_excessive += 1
        print >> out
      return n_excessive
    sel = (self.sites_count != 0).iselection()
    n_excessive = show_selection(i_ncs=0, pair=[sel, sel], op=None)
    for i_ncs,pair,op in zip(count(1),
                             self.group.selection_pairs,
                             self.group.matrices):
      n_excessive += show_selection(i_ncs=i_ncs, pair=pair, op=op)
    return n_excessive

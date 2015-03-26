from __future__ import division
# LIBTBX_SET_DISPATCHER_NAME phenix.secondary_structure_restraints

from mmtbx.secondary_structure import *
from mmtbx.geometry_restraints import hbond
import iotbx.pdb
import iotbx.phil
from scitbx.array_family import flex
from libtbx.utils import Sorry
import cStringIO
import sys

def run (args, out=sys.stdout, log=sys.stderr) :
  pdb_files = []
  sources = []
  force_new_annotation = False
  master_phil_str = """
show_all_params = False
  .type = bool
filter_outliers = True
  .type = bool
format = *phenix phenix_bonds pymol refmac kinemage
  .type = choice
quiet = False
  .type = bool
file_name = None
  .type = path
  .multiple = True
  .optional = True
  .style = hidden
  %s
""" % sec_str_master_phil_str
  pcl = iotbx.phil.process_command_line_with_files(
    args=args,
    master_phil_string=master_phil_str,
    pdb_file_def="file_name")

  from mmtbx.secondary_structure import sec_str_master_phil
  work_params = pcl.work.extract()
  if work_params.quiet :
    out = cStringIO.StringIO()
  pdb_files = work_params.file_name
  if len(pdb_files) > 0 :
    work_params.file_name.extend(pdb_files)
  if len(pdb_files) == 0 :
    raise Sorry("No PDB files specified.")
  pdb_combined = iotbx.pdb.combine_unique_pdb_files(file_names=pdb_files)
  pdb_structure = iotbx.pdb.input(source_info=None,
    lines=flex.std_string(pdb_combined.raw_records))

  # processing pdb
  from mmtbx.monomer_library import pdb_interpretation, server
  import mmtbx
  import mmtbx.command_line.geometry_minimization

  mon_lib_srv = server.server()
  ener_lib = server.ener_lib()
  defpars = mmtbx.command_line.geometry_minimization.master_params().extract()

  processed_pdb_file = pdb_interpretation.process(
    mon_lib_srv    = mon_lib_srv,
    ener_lib       = ener_lib,
    pdb_inp        = pdb_structure,
    params         = defpars.pdb_interpretation,
    force_symmetry = True)
  pdb_hierarchy = processed_pdb_file.all_chain_proxies.pdb_hierarchy
  geometry = processed_pdb_file.geometry_restraints_manager()
  geometry.pair_proxies(processed_pdb_file.xray_structure().sites_cart())
  pdb_hierarchy.atoms().reset_i_seq()
  if len(pdb_hierarchy.models()) != 1 :
    raise Sorry("Multiple models not supported.")
  m = manager(pdb_hierarchy=pdb_hierarchy,
    geometry_restraints_manager=geometry,
    sec_str_from_pdb_file=pdb_structure.extract_secondary_structure(),
    params=work_params.secondary_structure)
  m.find_automatically(log=log)

  # bp_p = nucleic_acids.get_basepair_plane_proxies(
  #     pdb_hierarchy,
  #     m.params.secondary_structure.nucleic_acid.base_pair,
  #     geometry)
  # st_p = nucleic_acids.get_stacking_proxies(
  #     pdb_hierarchy,
  #     m.params.secondary_structure.nucleic_acid.stacking_pair,
  #     geometry)
  # hb_b, hb_a = nucleic_acids.get_basepair_hbond_proxies(pdb_hierarchy,
  #     m.params.secondary_structure.nucleic_acid.base_pair)

  prefix_scope="refinement.pdb_interpretation"
  if (work_params.format != "phenix") :
    prefix_scope = ""
  ss_phil = None
  working_phil = m.as_phil_str(master_phil=sec_str_master_phil)
  phil_diff = sec_str_master_phil.fetch_diff(source=working_phil)
  if work_params.format == "phenix_bonds" :
    raise Sorry("Not yet implemented.")
  elif work_params.format in ["pymol", "refmac", "kinemage"] :
    m.show_summary(out=log)
    build_proxies = m.create_hbond_proxies(
      log=log,
      as_python_objects=True)
    if (len(build_proxies.proxies) == 0) :
      pass
    elif work_params.format == "pymol" :
      hbond.as_pymol_dashes(
        proxies=build_proxies.proxies,
        pdb_hierarchy=pdb_hierarchy,
        filter=work_params.filter_outliers,
        out=out)
    elif work_params.format == "kinemage" :
      hbond.as_kinemage(
        proxies=build_proxies.proxies,
        pdb_hierarchy=pdb_hierarchy,
        filter=work_params.filter_outliers,
        out=out)
    else :
      hbond.as_refmac_restraints(
        proxies=build_proxies.proxies,
        pdb_hierarchy=pdb_hierarchy,
        filter=work_params.filter_outliers,
        out=out)
  else :
    print >> out, "# These parameters are suitable for use in phenix.refine."
    if (prefix_scope != "") :
      print >> out, "%s {" % prefix_scope
    if work_params.show_all_params :
      working_phil.show(prefix="  ", out=out)
    else :
      phil_diff.show(prefix="  ", out=out)
    if (prefix_scope != "") :
      print >> out, "}"
    return working_phil.as_str()

if __name__ == "__main__" :
  run(sys.argv[1:])

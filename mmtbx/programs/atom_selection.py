from __future__ import division, print_function

from libtbx.program_template import ProgramTemplate
from libtbx.str_utils import show_string
from libtbx.utils import plural_s
from cctbx.array_family import flex
from cctbx import crystal, uctbx, xray
import mmtbx.model
import iotbx.pdb
from libtbx.utils import Sorry

class Program(ProgramTemplate):

  description = '''
phenix.pdb_atom_selection: tool for selecting some atoms and optionally
  write out them as a PDB file

Usage examples:
  phenix.pdb_atom_selection model.pdb "chain A"
  phenix.pdb_atom_selection model.pdb "chain A" --write-pdb-file=sel.pdb
  '''

  datatypes = ['model', 'phil']

  master_phil_str = """
  atom_selection_program {
    inselection = None
      .type = atom_selection
      .help = what to select
      .multiple = True
    cryst1_replacement_buffer_layer = None
      .type = float
      .help = replace original symmetry with P1 and size that is sufficient to \
        place molecule and surround it with this amount of empty space
    write_pdb_file = None
      .type = path
  }
"""

  # ---------------------------------------------------------------------------
  def validate(self):
    print('Validating inputs', file=self.logger)
    self.data_manager.has_models(raise_sorry=True)
    if (self.params.atom_selection_program.inselection is None or
        len(self.params.atom_selection_program.inselection) == 0):
      raise Sorry("Need selections")

  # ---------------------------------------------------------------------------
  def run(self):
    # I'm guessing self.data_manager, self.params and self.logger
    # are already defined here...

    # this must be mmtbx.model.manager?
    model = self.data_manager.get_model()
    atoms = model.get_atoms()
    all_bsel = flex.bool(atoms.size(), False)
    for selection_string in self.params.atom_selection_program.inselection:
      print("Selecting '%s'" % selection_string, file=self.logger)
      isel = model.iselection(selstr=selection_string)
      all_bsel.set_selected(isel, True)
      if self.params.atom_selection_program.write_pdb_file is None:
        print("  %d atom%s selected" % plural_s(isel.size()), file=self.logger)
        for atom in atoms.select(isel):
          print ("    %s" % atom.format_atom_record(), file=self.logger)
    print("", file=self.logger)
    if self.params.atom_selection_program.write_pdb_file is not None:
      print ("Writing file:", show_string(self.params.atom_selection_program.write_pdb_file),file=self.logger)
      selected_model = model.select(all_bsel)
      if self.params.atom_selection_program.cryst1_replacement_buffer_layer is not None:
        box = uctbx.non_crystallographic_unit_cell_with_the_sites_in_its_center(
            sites_cart=selected_model.get_atoms().extract_xyz(),
            buffer_layer=self.params.atom_selection_program.cryst1_replacement_buffer_layer)
        sp = crystal.special_position_settings(box.crystal_symmetry())
        sites_frac = box.sites_frac()
        xrs_box = selected_model.get_xray_structure().replace_sites_frac(box.sites_frac())
        xray_structure_box = xray.structure(sp, xrs_box.scatterers())
        selected_model.set_xray_structure(xray_structure_box)
      pdb_str = selected_model.model_as_pdb()
      f = open(self.params.atom_selection_program.write_pdb_file, 'w')
      f.write(pdb_str)
      f.close()
      print("", file=self.logger)

  # ---------------------------------------------------------------------------
  def get_results(self):
    return None

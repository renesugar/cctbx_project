from __future__ import division, print_function
'''
'''
import os

from libtbx.data_manager import DataManagerBase
from libtbx.utils import Sorry
from scitbx.array_family import flex

# =============================================================================
class RealMapDataManager(DataManagerBase):

  datatype = 'real_map'

  # ---------------------------------------------------------------------------
  # Real-space Maps
  def add_real_map(self, filename, data):
    return self._add(RealMapDataManager.datatype, filename, data)

  def set_default_real_map(self, filename):
    return self._set_default(RealMapDataManager.datatype, filename)

  def get_real_map(self, filename=None):
    return self._get(RealMapDataManager.datatype, filename)

  def get_real_map_names(self):
    return self._get_names(RealMapDataManager.datatype)

  def get_default_real_map_name(self):
    return self._get_default_name(RealMapDataManager.datatype)

  def remove_real_map(self, filename):
    return self._remove(RealMapDataManager.datatype, filename)

  def has_real_maps(self, expected_n=1, exact_count=False, raise_sorry=False):
    return self._has_data(RealMapDataManager.datatype, expected_n=expected_n,
                          exact_count=exact_count, raise_sorry=raise_sorry)

  def process_real_map_file(self, filename):
    return self._process_file(RealMapDataManager.datatype, filename)

  def write_real_map_file(self, filename, unit_cell, space_group,
                          map_data, labels, overwrite=False):
    # wrapper for iotbx.ccp4_map.write_ccp4_map
    # potentially move to mrcfile (https://github.com/ccpem/mrcfile)
    if (os.path.isfile(filename) and (not overwrite)):
      raise Sorry('%s already exists and overwrite is set to %s.' %
                  (filename, overwrite))
    import iotbx.ccp4_map

    # check labels (maybe other arugments?)
    if (not isinstance(labels, flex.std_string)):
      try:
        labels = flex.std_string(labels)
      except Exception as err:
        # trap Boost.Python.ArgumentError
        if (str(err).startswith('Python argument types in')):
          raise Sorry('A list of strings is required for the "labels" argument')
        else:
          raise

    try:
      iotbx.ccp4_map.write_ccp4_map(
        file_name = filename,
        unit_cell = unit_cell,
        space_group = space_group,
        map_data = map_data,
        labels = labels
      )
    except IOError as err:
      raise Sorry('There was an error with writing %s.\n%s' %
                  (filename, err))

    self._output_files.append(filename)
    self._output_types.append(RealMapDataManager.datatype)

# =============================================================================
# end

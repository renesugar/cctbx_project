# LIBTBX_SET_DISPATCHER_NAME cctbx_regression.test_nightly

from __future__ import division
from libtbx.command_line import run_tests_parallel
import sys, os
import libtbx.load_env

if (__name__ == "__main__") :
  args = [
    "module=libtbx",
    "module=boost_adaptbx",
    "module=scitbx",
    "module=cctbx",
    "module=iotbx",
    "module=smtbx",
    "nproc=Auto",
  ]
  if 'dxtbx' in libtbx.env.module_dict:
    args.append("module=dxtbx")

  if (libtbx.env.find_in_repositories("chem_data") is not None and
      os.path.exists(libtbx.env.find_in_repositories("chem_data"))):
    args.append("module=mmtbx")

  if (run_tests_parallel.run(args) > 0) :
    sys.exit(1)

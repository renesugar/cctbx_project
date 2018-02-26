
from __future__ import division
import libtbx.test_utils.parallel
from libtbx.utils import Sorry, Usage
import libtbx.phil
import random
import os
import sys

master_phil = libtbx.phil.parse("""
directory = None
  .type = path
  .multiple = True
module = None
  .type = str
  .multiple = True
script = None
  .type = path
  .multiple = True
nproc = 1
  .type=  int
shuffle = False
  .type = bool
quiet = False
  .type = bool
verbosity = 1
  .type = int
stderr = False
  .type = bool
run_in_tmp_dir = False
  .type = bool
max_time = 180
  .type = float(value_min=0)
  .help = "Print warning and timing for all tests that take longer"
          "than max_time (in seconds) to run."
""")

def run (args, return_list_of_tests=None) :
  if (len(args) == 0) :
    raise Usage("""libtbx.run_tests_parallel [module=NAME] [directory=path]""")
  user_phil = []
  for arg in args :
    if os.path.isdir(arg) :
      user_phil.append(libtbx.phil.parse("directory=%s" % arg))
    else :
      try :
        arg_phil = libtbx.phil.parse(arg)
      except RuntimeError :
        raise Sorry("Unrecognized argument '%s'" % arg)
      else :
        user_phil.append(arg_phil)

  params = master_phil.fetch(sources=user_phil).extract()

  if params.run_in_tmp_dir:
    from libtbx.test_utils import open_tmp_directory
    run_dir = open_tmp_directory()
    print 'Running tests in %s' % run_dir
    os.chdir(run_dir)
  elif return_list_of_tests:
    pass # don't need to check anything
  else:
    cwd = os.getcwd()
    cwd_files = os.listdir(cwd)
    if (len(cwd_files) > 0) :
      raise Sorry("Please run this program in an empty directory.")
  if (len(params.directory) == 0) and (len(params.module) == 0) :
    raise Sorry("Please specify modules and/or directories to test.")
  all_tests = []
  all_tests.extend(libtbx.test_utils.parallel.make_commands(params.script))
  for dir_name in params.directory :
    if os.path.split(dir_name)[-1].find("cctbx_project")>-1:
      print 'DANGER '*10
      print 'Using the directory option in cctbx_project can be very time consuming'
      print 'DANGER '*10
    dir_tests = libtbx.test_utils.parallel.find_tests(dir_name)
    all_tests.extend(libtbx.test_utils.parallel.make_commands(dir_tests))
  for module_name in params.module :
    module_tests = libtbx.test_utils.parallel.get_module_tests(module_name)
    all_tests.extend(module_tests)

  if return_list_of_tests:
    return all_tests

  if (len(all_tests) == 0) :
    raise Sorry("No test scripts found in %s." % params.directory)
  if (params.shuffle) :
    random.shuffle(all_tests)
  if (params.quiet) :
    params.verbosity = 0
  log = open("run_tests_parallel_zlog", "wb")
  result = libtbx.test_utils.parallel.run_command_list(
    cmd_list=all_tests,
    nprocs=params.nproc,
    log=log,
    verbosity=params.verbosity,
    max_time=params.max_time)
  log.close()
  print """\nSee run_tests_parallel_zlog for full output.\n"""
  if (result.failure > 0) :
    print ""
    print "*" * 80
    print "ERROR: %d TEST FAILURES.  PLEASE FIX BEFORE COMMITTING CODE." % \
      result.failure
    print "*" * 80
    print ""
  return result.failure

if (__name__ == "__main__") :
  if (run(sys.argv[1:]) > 0) :
    sys.exit(1)

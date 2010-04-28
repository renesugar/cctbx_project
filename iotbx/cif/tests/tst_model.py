from cctbx.array_family import flex
from libtbx.test_utils import Exception_expected

def exercise_cif_model():
  import iotbx.cif
  if (not iotbx.cif.has_antlr3):
    print "Skipping tst_model.py (antlr3 is not available)"
    return
  from iotbx.cif import model
  cif_model = model.cif()
  #
  loop = model.loop()
  loop["_loop_a"] = (1,2,3)
  loop.add_columns({'_loop_c': [4,5,6],
                    '_loop_b': ['7','8','9']})
  loop.add_row((4,7,'0'))
  try: loop["_loop_invalid"] = (7,8)
  except AssertionError: pass
  else: raise Exception_expected
  assert len(loop) == 3 # the number of columns (keys)
  assert loop.size() == 4 # the number of rows (loop iterations)
  assert loop.keys() == ['_loop_a', '_loop_c', '_loop_b']
  loop2 = model.loop(header=("_loop2_a", "_loop2_b"), data=(1,2,3,4,5,6))
  assert loop2.keys() == ["_loop2_a", "_loop2_b"]
  assert loop2.values() == [flex.std_string(['1', '3', '5']),
                            flex.std_string(['2', '4', '6'])]
  #
  block = model.block()
  block["_tag"] = 3
  block["_tag1"] = "a string"
  block["_another_tag"] = 3.142
  assert "_tag" in block
  assert "_tag1" in block
  assert "_another_tag" in block
  assert block["_tag"] == '3'
  assert block["_tag1"] == "a string"
  assert block["_another_tag"] == "3.142"
  assert block.keys() == ['_tag', '_tag1', '_another_tag']
  assert block.values() == ["3", 'a string', "3.142"]
  block.add_loop(loop)
  assert len(block) == 6
  assert block.items() == [
    ('_tag', '3'), ('_tag1', 'a string'), ('_another_tag', '3.142'),
    ('_loop_a', flex.std_string(['1', '2', '3', '4'])),
    ('_loop_c', flex.std_string(['4', '5', '6', '7'])),
    ('_loop_b', flex.std_string(['7', '8', '9', '0']))]
  #
  cif_model["fred"] = block
  assert "fred" in cif_model
  assert cif_model["fred"] is block
  assert cif_model["fred"]["_tag"] == '3'
  cif_model["fred"]["_tag"] = 4
  assert cif_model["fred"]["_tag"] == '4'
  del cif_model["fred"]["_tag"]
  try: cif_model["fred"]["_tag"]
  except KeyError: pass
  else: raise Exception_expected

if __name__ == '__main__':
  exercise_cif_model()
  print "OK"

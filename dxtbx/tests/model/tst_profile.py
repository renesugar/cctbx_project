
from __future__ import absolute_import, division

from dxtbx.model import ProfileModelBaseIface, ProfileModelFactory

class NullProfile(ProfileModelBaseIface):

  name = 'null'

  def __init__(self, parameter):
    self.parameter = parameter

  def to_dict(self):
    return {
      '__id__' : self.name,
      'parameter' : self.parameter
    }

  @classmethod
  def from_dict(cls, obj):
    return cls(obj['parameter'])

ProfileModelFactory.append(NullProfile.name, NullProfile)


class Test(object):

  def __init__(self):
    pass

  def run(self):
    profile1 = NullProfile(10)
    dictionary = profile1.to_dict()
    profile2 = ProfileModelFactory.from_dict(dictionary)
    assert(profile1.parameter == profile2.parameter)
    print 'OK'

if __name__ == '__main__':
  test = Test()
  test.run()

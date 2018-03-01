#!/usr/bin/python

from __future__ import division
from installer_utils import *
import os
import sys

def _generate_pangorc(base_dir):
  return """
#
# Auto-generated file, do not change
#

[Pango]
ModulesPath = %s/lib/pango/1.6.0/modules/
ModuleFiles = %s/etc/pango/pango.modules

[PangoX]
AliasFiles = %s/etc/pango/pangox.aliases
""" % (base_dir, base_dir, base_dir)


def check_pango(base_dir):
  '''Determine whether there is a consistent pangorc file at this location'''

  try:
    pangorc = os.path.join(base_dir, "etc", "pango", "pangorc")
    if not os.path.isfile(pangorc):
      return False
    pango_file = open(pangorc, 'r')
    settings = pango_file.read()
    pango_file.close()
    if settings != _generate_pangorc(base_dir):
      return False
    return True
  except Exception:
    return False


def fix_pango(base_dir, out):
  '''Fix the pango configuration files'''

  pango_dir = os.path.join(base_dir, "etc", "pango")
  if not os.path.isdir(pango_dir):
    print >> out, "%s not present, could not regenerate pango files" % pango_dir
    # Should really be an exception, but cannot do that because of buildbot
    return

  # pangorc
  pangorc = os.path.join(pango_dir, "pangorc")
  print >> out, "generating pangorc file at %s" % pangorc
  open(pangorc, "w").write(_generate_pangorc(base_dir))

  os.environ['PANGO_RC_FILE'] = pangorc

  # pango.modules
  pangomodules = "%s/pango.modules" % pango_dir
  print >> out, "generating pango.modules file at %s" % pangomodules
  call(("%s/bin/pango-querymodules > %s") % (base_dir, pangomodules), log=out)


def fix_gtk(base_dir, out): #--- Gtk+
  gtk_dir = os.path.join(base_dir, "etc", "gtk-2.0")
  if not os.path.isdir(gtk_dir):
    print >> out, "%s not present, could not regenerate gdk-pixbuf.loaders" % gtk_dir
    return

  # gtk.immodules
  print >> out, "generating gtk.immodules file"
  call(("%s/bin/gtk-query-immodules-2.0 %s/lib/gtk-2.0/2.10.0/immodules/*.so"
        + "> %s/etc/gtk-2.0/gtk.immodules") % (base_dir, base_dir, base_dir),
        log=out)
  # gdk-pixbuf.loaders
  print >> out, "generating gdk-pixbuf.loaders file"
  call(("%s/bin/gdk-pixbuf-query-loaders %s/lib/gdk-pixbuf-2.0/2.10.0/loaders/*.so"+
        " > %s/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache") % (base_dir, base_dir,
          base_dir), log=out)
  call(("%s/bin/gdk-pixbuf-query-loaders %s/lib/gdk-pixbuf-2.0/2.10.0/loaders/*.so"+
        " > %s/etc/gtk-2.0/gdk-pixbuf.loaders") % (base_dir, base_dir,
          base_dir), log=out)


def fix_fonts(base_dir, out): #--- Fonts
  fonts_share_dir = os.path.join(base_dir, "share", "fonts")
  fonts_etc_dir = os.path.join(base_dir, "etc", "fonts")
  fonts_cache_dir = os.path.join(base_dir, 'var', 'cache', 'fontconfig')
  if not os.path.isdir(fonts_etc_dir):
    print >> out, "%s not present, could not rebuild fonts" % fonts_etc_dir
    return

  print >> out, "updating fonts/local.conf file"
  fonts_in = open(os.path.join(fonts_share_dir, "local.conf.in"))
  fonts_out = open(os.path.join(fonts_etc_dir, "local.conf"), "w")
  for line in fonts_in.readlines():
    if ('FONTCONFIG_PATH' in line):
      line = line.replace('FONTCONFIG_PATH', fonts_share_dir)
    if ('FONTCACHE_PATH' in line):
      line = line.replace('FONTCACHE_PATH', fonts_cache_dir)
    fonts_out.write(line)
  fonts_in.close()
  fonts_out.close()

  os.environ['FONTCONFIG_PATH'] = fonts_etc_dir

  try:
    print >> out, "running mkfontscale/mkfontdir on %s" % fonts_share_dir
    call("mkfontscale %s" % fonts_share_dir, log=out)
    call("mkfontdir %s" % fonts_share_dir, log=out)
    print >> out, "rebuilding font cache"
    call("%s/bin/fc-cache -v %s" % (base_dir, fonts_share_dir), log=out)
  except Exception:
    print >> out, "rebuilding fonts failed"
    pass


def fix_themes(base_dir, out): #--- Themes
  share_dir = os.path.join(base_dir, "share")
  if not os.path.isdir(share_dir):
    print >> out, "problem with installation, could not make index.theme file"
    return

  print >> out, "generating index.theme file"
  hicolor_dir = os.path.join(share_dir, "icons", "hicolor")
  try:
    os.makedirs(hicolor_dir)
  except Exception:
    pass
  open(os.path.join(hicolor_dir, "index.theme"), "w").write("""
#
# Auto-generated, do not change'
#
[Icon Theme]
Name=Hicolor
Comment=Fallback icon theme
Hidden=true
Directories=48x48/filesystems

[48x48/filesystems]
Size=48
Context=FileSystems
Type=Threshold
""")


def run(base_dir, out=sys.stdout, only_if_needed=False):
  if only_if_needed and check_pango(base_dir):
    return

  if not sys.platform.startswith('linux'):
    print >> out, "This script is only applicable to Linux - exiting."
    return

  print >> out, "Regenerating module files in %s" % base_dir

  if os.path.exists(os.path.join(base_dir, 'conda-meta')):
    print >>out, "Base directory created using conda. Skipping module file regeneration"
    return

  if not os.path.exists(base_dir):
    if only_if_needed:
      print >> out, "Base directory '%s' does not exist." % base_dir
      print >> out, "  Assuming base-less installation, skipping module file regeneration"
      return
    raise OSError("Base directory '%s' does not exist." % base_dir)

  fix_pango(base_dir, out)
  fix_gtk(base_dir, out)
  fix_fonts(base_dir, out)
  fix_themes(base_dir, out)


if (__name__ == "__main__") :
  from optparse import OptionParser
  import libtbx.load_env

  default_location = libtbx.env.under_base('.')

  parser = OptionParser(
    description="Generate new config files for various third-party modules " +
      "required for the graphical interface (if any).")
  parser.add_option("--base_dir", dest="base_dir", action="store",
    help="Base directory of the CCTBX installation (%s)" % default_location, default=default_location)
  parser.add_option("--check", dest="check", action="store_true",
    help="Only run if current files are not consistent", default=False)

  options, args = parser.parse_args(sys.argv[1:])
  run(options.base_dir, only_if_needed=options.check)

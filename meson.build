project ('ueberzug', 'c')

py = import('python').find_installation(pure: false)

# not sure what your minimum x lib versions are,
# but you could specify them here
x_deps = [
  dependency('x11'),
  dependency('xext'),
  dependency('xres'),
]

x_sources = [
  'ueberzug/X/X.c',
  'ueberzug/X/Xshm.c',
  'ueberzug/X/display.c',
  'ueberzug/X/window.c',
]

# copies the python source directory to the install directory
install_subdir(
  'ueberzug',
  install_dir: py.get_install_dir(),
  exclude_directories: 'X',
)

# also install the c extension to the same install directory
py.extension_module(
  'X',
  x_sources,
  dependencies: x_deps,
  install: true,
  subdir: 'ueberzug',
)

# print out a summary of settings
# note this won't be directly visible with meon-python
# since that suppresses certain meson output by default
# and deletes its build directory when it is done (so
# you can't find the logfile)
#
# if you just want to see this, try running a meson setup
# command without actually building anything.
# e.g. $ meson setup _build --prefix=/your/prefix
summary(
  {
    'prefix': get_option('prefix'),
    'bindir': get_option('bindir'),
    'libdir': get_option('libdir'),
    'datadir': get_option('datadir'),
    'py_install_dir': py.get_install_dir(),
  },
  section: 'Directories'
)

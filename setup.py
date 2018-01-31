from setuptools import setup
from setuptools.command.install import install
from setuptools import Distribution as _Distribution
import setuptools.command
import mymod
import os
from distutils.command.install_data import install_data as _install_data
from distutils.util import change_root, convert_path
from distutils.file_util import write_file
from distutils import log
import glob
import subprocess

sysconfdir = '/etc'
tuned_profiles_dir = '/usr/lib/tuned'
tuned_recommend_dir = '%s/recommend.d' % tuned_profiles_dir
datadir = '/usr/share'
docdir = datadir + '/doc/tuned'

tmpfilesdir_fallback = '/usr/lib/tmpfiles.d'
p = subprocess.Popen("pkg-config systemd --variable tmpfilesdir " \
		+ "|| rpm --eval '%{_tmpfilesdir}' 2>/dev/null " \
		+ "|| echo %s" % tmpfilesdir_fallback, \
		shell = True, universal_newlines = True, \
		stdout = subprocess.PIPE)
out, err = p.communicate()
tmpfilesdir_detect = out.strip()
tmpfilesdir = tmpfilesdir_detect.replace('%{_tmpfilesdir}', \
		tmpfilesdir_fallback)

unitdir_fallback = '/usr/lib/systemd/system'
p = subprocess.Popen("pkg-config systemd --variable systemdsystemunitdir " \
		+ "|| rpm --eval '%{_unitdir}' 2>/dev/null " \
		+ "|| echo %s" % unitdir_fallback, \
		shell = True, universal_newlines = True, \
		stdout = subprocess.PIPE)
out, err = p.communicate()
unitdir_detect = out.strip()
unitdir = unitdir_detect.replace('%{_unitdir}', unitdir_fallback)

man_pages = []
for section in [5, 7, 8]:
	files = glob.glob('man/*.%d' % section)
	man_pages.append(('%s/man/man%d' % (datadir, section), files))

docfiles = glob.glob('doc/*')
docfiles = [(docdir, docfiles)]

profiles = [x for x in os.listdir('profiles') if os.path.isdir('profiles/%s' % x)]
profile_files = []
for profile in profiles:
	destdir = '%s/%s' % (tuned_profiles_dir, profile)
	files = ['profiles/%s/tuned.conf' % profile]
	files += glob.glob('profiles/%s/*.sh' % profile)
	profile_files.append((destdir, files))
variable_confs = []
for profile in profiles:
	destdir = '%s/tuned' % sysconfdir
	files = glob.glob('profiles/%s/*variables*' % profile)
	variable_confs.append((destdir, files))

class Distribution(_Distribution):
	def __init__(self, *args, **kwargs):
		self.renamed_data_files = []
		self.empty_files = []
		self.desktop_files = []
		_Distribution.__init__(self, *args, **kwargs)

class install_data(_install_data):
	def initialize_options(self):
		_install_data.initialize_options(self)
		self.renamed_data_files = self.distribution.renamed_data_files
		self.empty_files = self.distribution.empty_files
		self.desktop_files = self.distribution.desktop_files
	
	# Inspired by install_data:run from distutils.command.install_data
	def _install_renamed(self):
		for dest_dir, files in self.renamed_data_files:
			dest_dir = convert_path(dest_dir)
			if not os.path.isabs(dest_dir):
				dest_dir = os.path.join(self.install_dir, dest_dir)
			elif self.root:
				dest_dir = change_root(self.root, dest_dir)
			self.mkpath(dest_dir)
			if len(files) == 0:
				# If there are no files listed, the user must be
				# trying to create an empty directory, so add the
				# directory to the list of output files.
				self.outfiles.append(dest_dir)
			else:
				for source, new_name in files:
					source = convert_path(source)
					dest = os.path.join(dest_dir, new_name)
					(out, _) = self.copy_file(source, dest)
					self.outfiles.append(out)

	def _install_empty(self):
		for f in self.empty_files:
			f = convert_path(f)
			if not os.path.isabs(f):
				f = os.path.join(self.install_dir, f)
			elif self.root:
				f = change_root(self.root, f)
			self.mkpath(os.path.dirname(f))
			log.info('creating file %s' % f)
			write_file(f, [])
			self.outfiles.append(f)

	def _install_desktop_files(self):
		dir = '%s/applications' % datadir
		if self.root:
			dir = change_root(self.root, dir)
		self.mkpath(dir)
		for f in self.desktop_files:
			log.info('installing desktop file %s' % f)
			os.system('desktop-file-install --dir=%s %s' % (dir, f))

	def run(self):
		_install_data.run(self)
		self._install_renamed()
		self._install_empty()
		self._install_desktop_files()

setup(name = 'tuned',
		version = '2.9.0',
		description = 'A tuning daemon',
		distclass = Distribution,
		packages = ['tuned', 'tuned.units', 'tuned.monitors',
				'tuned.storage', 'tuned.utils', 'tuned.daemon',
				'tuned.profiles', 'tuned.profiles.functions',
				'tuned.hardware', 'tuned.exports', 'tuned.gtk',
				'tuned.plugins', 'tuned.plugins.instance',
				'tuned.admin'
				],
		cmdclass = { 'install_data': install_data },
		data_files = [
				('%s/tuned/ui' % datadir, ['tuned-gui.glade']),
				('%s/tuned' % sysconfdir, ['bootcmdline']),
				(tuned_profiles_dir, ['profiles/functions']),
				(unitdir, ['tuned.service']),
				('%s/grub.d' % sysconfdir, ['00_tuned']),
				('%s/polkit-1/actions' % datadir, [
						'com.redhat.tuned.policy',
						'com.redhat.tuned.gui.policy',
						]),
				(docdir, ['AUTHORS', 'COPYING', 'README']),
				('%s/icons/hicolor/scalable/apps' % datadir, ['icons/tuned.svg']),
				] + profile_files + variable_confs + man_pages + docfiles,
		renamed_data_files = [
				('%s/dbus-1/system.d' % sysconfdir, [('dbus.conf','com.redhat.tuned.conf')]),
				('%s/modprobe.d' % sysconfdir, [('modules.conf', 'tuned.conf')]),
				(tuned_recommend_dir, [('recommend.conf', '50-tuned.conf')]),
				('%s/bash-completion/completions' % datadir, [('tuned-adm.bash', 'tuned-adm')]),
				(tmpfilesdir, [('tuned.tmpfiles', 'tuned.conf')]),
				],
		desktop_files = ['tuned-gui.desktop'],
		empty_files = [
				'%s/tuned/active_profile' % sysconfdir,
				'%s/tuned/profile_mode' % sysconfdir,
				],
		)

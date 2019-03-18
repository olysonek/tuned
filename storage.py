import os
import tuned.consts as consts

class Storage(object):
	def __init__(self, persistent_dir = consts.PERSISTENT_STORAGE_DIR,
			runtime_dir = consts.RUNTIME_STORAGE_DIR,
			parent = None)
		self._persistent_dir = persistent_dir
		self._runtime_dir = runtime_dir
		self._parent = parent
		self._substores = {} # directory name: Storage
		self._persistent_files = {} # file name: object
		self._runtime_files = {}

	def create_substore(self, namespace):
		persistent_dir = os.path.join(self._persistent_dir, namespace)
		runtime_dir = os.path.join(self._runtime_dir, namespace)
		substore = Storage(persistent_dir = persistent_dir,
				runtime_dir = runtime_dir,
				parent = self)
		return substore

	def _get_path(self, filename, persistent):
		if persistent:
			path = self._persistent_dir
		else:
			path = self._runtime_dir
		return os.path.join(path, filename)

	def get_data(self, filename, persistent):
		if persistent:
			return self._persistent_files.setdefault(filename)
		else:
			return self._runtime_files.setdefault(filename)

	def save_file(self, filename, persistent):
		data = self.get_data(filename, persistent)
		encoded = data.encode() # TODO
		path = self._get_path(filename, persistent)
		with open(path, "w") as f:
			f.write(contents)

	def _replace_data(self, filename, persistent, data):
		if persistent:
			self._persistent_files[filename] = data
		else:
			self._runtime_files[filename] = data

	def load_file(self, filename, persistent):
		path = self._get_path(filename, persistent)
		encoded = read path # TODO
		data = encoded.decode() # TODO
		self._replace_data(filename, persistent, data)
		return data

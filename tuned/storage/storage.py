import os
import tuned.consts as consts
import json

class Storage(object):
	def __init__(self, persistent_dir = consts.PERSISTENT_STORAGE_DIR,
			runtime_dir = consts.RUNTIME_STORAGE_DIR,
			parent = None):
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
		self._substores[namespace] = substore
		return substore

	def _get_directory(self, persistent):
		if persistent:
			return self._persistent_dir
		else:
			return self._runtime_dir

	def _get_path(self, filename, persistent):
		path = self._get_directory(persistent)
		return os.path.join(path, filename)

	def get_data(self, filename, persistent):
		if persistent:
			return self._persistent_files.setdefault(filename, {})
		else:
			return self._runtime_files.setdefault(filename, {})

	def _create_dir(self, persistent):
		if self._parent is not None:
			self._parent._create_dir(persistent)
		path = self._get_directory(persistent)
		os.mkdir(path)

	def _encode(self, obj):
		return json.dumps(obj)

	def _decode(self, s)
		return json.loads(s)

	def save_file(self, filename, persistent):
		data = self.get_data(filename, persistent)
		encoded = self._encode(data)
		self._create_dir(persistent)
		path = self._get_path(filename, persistent)
		with open(path, "w") as f:
			f.write(encoded)

	def _replace_data(self, filename, persistent, data):
		if persistent:
			self._persistent_files[filename] = data
		else:
			self._runtime_files[filename] = data

	def load_file(self, filename, persistent):
		path = self._get_path(filename, persistent)
		with open(path, "r") as f:
			encoded = f.read()
		data = self._decode(encoded)
		self._replace_data(filename, persistent, data)
		return data

	def delete_file(self, filename, persistent):
		if persistent:
			files = self._persistent_files
		else:
			files = self._runtime_files
		del files[filename]
		try:
			os.unlink(filename)
		except:
			pass

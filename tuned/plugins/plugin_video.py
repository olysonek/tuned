import base
from decorators import *
import tuned.logs
from tuned.utils.commands import commands
import os

log = tuned.logs.get()

class VideoPlugin(base.Plugin):
	"""
	Plugin for tuning powersave options for some graphic cards.
	"""

	def _init_devices(self):
		self._devices_supported = True
		self._free_devices = set()
		self._assigned_devices = set()

		# FIXME: this is a blind shot, needs testing
		for device in self._hardware_inventory.get_devices("drm").match_sys_name("card*").match_property("DEVTYPE", "drm_minor"):
			self._free_devices.add(device.sys_name)

		self._cmd = commands()

	def _get_device_objects(self, devices):
		return map(lambda x: self._hardware_inventory.get_device("drm", x), devices)

	@classmethod
	def _get_config_options(self):
		return {
			"radeon_powersave" : None,
			"radeon_dpm_state" : None,
		}

	def _instance_init(self, instance):
		instance._has_dynamic_tuning = False
		instance._has_static_tuning = True

	def _instance_cleanup(self, instance):
		pass

	def _radeon_powersave_files(self, device):
		return {
			"method" : "/sys/class/drm/%s/device/power_method" % device,
			"profile": "/sys/class/drm/%s/device/power_profile" % device,
		}

	def _radeon_dpm_state_file(self, device):
		return "/sys/class/drm/%s/device/power_dpm_state" % device

	@command_set("radeon_powersave", per_device=True)
	def _set_radeon_powersave(self, value, device, sim):
		sys_files = self._radeon_powersave_files(device)
		if not os.path.exists(sys_files["method"]):
			if not sim:
				log.warn("radeon_powersave is not supported on '%s'" % device)
				return None

		if value in ["default", "auto", "low", "mid", "high"]:
			if not sim:
				self._cmd.write_to_file(sys_files["method"], "profile")
				self._cmd.write_to_file(sys_files["profile"], value)
			return value
		elif value == "dynpm":
			if not sim:
				self._cmd.write_to_file(sys_files["method"], "dynpm")
			return "dynpm"
		elif value == "dpm":
			if not sim and self._get_radeon_powersave(device) != "dpm":
				log.error("Cannot set dpm power method through the video plugin." \
						+ "Use the bootloader plugin with the 'cmdline = radeon.dpm=1' option")
				return None
			return "dpm"
		else:
			if not sim:
				log.warn("Invalid option for radeon_powersave.")
			return None


	@command_get("radeon_powersave")
	def _get_radeon_powersave(self, device):
		sys_files = self._radeon_powersave_files(device)
		method = self._cmd.read_file(sys_files["method"]).strip()
		if method == "profile":
			return self._cmd.read_file(sys_files["profile"]).strip()
		elif method == "dynpm" or method == "dpm":
			return method
		else:
			return None

	@command_set("radeon_dpm_state", per_device=True, priority=10)
	def _set_radeon_dpm_state(self, value, device, sim):
		if self._get_radeon_powersave(device) != "dpm":
			log.error("dpm power method is not enabled.")
			return None
		if not value in ["battery", "balanced", "performance"]:
			if not sim:
				log.warn("Invalid option for radeon_dpm_state.")
			return None
		path = self._radeon_dpm_state_file(device)
		self._cmd.write_to_file(path, value)
		return value

	@command_get("radeon_dpm_state")
	def _get_radeon_dpm_state(self, device):
		if self._get_radeon_powersave(device) != "dpm":
			log.error("dpm power method is not enabled.")
			return None
		path = self._radeon_dpm_state_file(device)
		return self._cmd.read_file(path).strip()

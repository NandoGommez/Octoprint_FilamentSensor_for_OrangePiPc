# coding=utf-8
from __future__ import absolute_import
import flask

import octoprint.plugin
from octoprint.events import Events
import OPi.GPIO as GPIO
from time import sleep
import subprocess


class FilamentSensorOrangePiPcPlugin(octoprint.plugin.StartupPlugin,
							 octoprint.plugin.EventHandlerPlugin,
							 octoprint.plugin.TemplatePlugin,
							 octoprint.plugin.SettingsPlugin,
							 octoprint.plugin.AssetPlugin,
							 octoprint.plugin.RestartNeedingPlugin):

	def initialize(self):
		self._logger.info("Running OPi.GPIO")
		GPIO.setwarnings(False)		# Disable GPIO warnings
		self.FilamentSensorOrangePiPcPlugin_confirmations_tracking = 0
		self.print_started = False
		self.filament_send_alert = False
		self.filament_send_alert_count = 0
		self.relay_send_alert = False
		self.relay_send_alert_count = 0

	@property
	def pin(self):
		return str(self._settings.get(["pin"]))

	@property
	def pin_relay_auto1(self):
		return str(self._settings.get(["pin_relay_auto1"]))

	@property
	def pin_relay_auto2(self):
		return str(self._settings.get(["pin_relay_auto2"]))

	@property
	def relay_auto1_timeon(self):
		return int(self._settings.get(["relay_auto1_timeon"]))

	@property
	def relay_auto1_timeout(self):
		return int(self._settings.get(["relay_auto1_timeout"]))

	@property
	def relay_auto2_timeon(self):
		return int(self._settings.get(["relay_auto2_timeon"]))

	@property
	def relay_auto2_timeout(self):
		return int(self._settings.get(["relay_auto2_timeout"]))

	@property
	def switch(self):
		return int(self._settings.get(["switch"]))

	@property
	def pin_relay(self):
		return str(self._settings.get(["pin_relay"]))

	@property
	def switch_pin_relay(self):
		return int(self._settings.get(["switch_pin_relay"]))

	@property
	def poll_time(self):
		return int(self._settings.get(["poll_time"]))

	@property
	def confirmations(self):
		return int(self._settings.get(["confirmations"]))

	@property
	def debug_mode(self):
		return int(self._settings.get(["debug_mode"]))

	@property
	def no_filament_gcode(self):
		return str(self._settings.get(["no_filament_gcode"])).splitlines()
	
	@property
	def gcode_relay(self):
		return str(self._settings.get(["gcode_relay"])).splitlines()

	@property
	def pause_print(self):
		return self._settings.get_boolean(["pause_print"])

	@property
	def send_webhook(self):
		return self._settings.get_boolean(["send_webhook"])

	@property
	def ifttt_applet_name_pin1(self):
		return str(self._settings.get(["ifttt_applet_name_pin1"]))

	@property
	def ifttt_applet_name_pin2(self):
		return str(self._settings.get(["ifttt_applet_name_pin2"]))

	@property
	def ifttt_secretkey(self):
		return str(self._settings.get(["ifttt_secretkey"]))

	def _setup_sensor(self):
		GPIO.cleanup()
		GPIO.setmode(GPIO.SUNXI)
		
		# Enable Filament Sensor
		if self.filament_sensor_enabled():
			self._logger.info("Filament Sensor active on GPIO Pin [%s]"%self.pin)
			GPIO.setup(self.pin, GPIO.IN)
			try:
				GPIO.remove_event_detect(self.pin)
			except:
				self._logger.info("Pin " + str(self.pin) + " not used before")

			GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self.filament_sensor_callback, bouncetime=self.poll_time)
		
		# Enable Relay Sensor
		if self.relay_sensor_enabled():
			self._logger.info("Relay Sensor active on GPIO Pin [%s]"%self.pin_relay)
			GPIO.setup(self.pin_relay, GPIO.IN)
			try:
				GPIO.remove_event_detect(self.pin_relay)
			except:
				self._logger.info("Pin " + str(self.pin_relay) + " not used before")

			GPIO.add_event_detect(self.pin_relay, GPIO.BOTH, callback=self.relay_sensor_callback, bouncetime=self.poll_time)

		# Enable Relay Auto 1
		if self.relay_auto1_enabled():
			self._logger.info("Relay Automation 1 active on GPIO Pin [%s]"%self.pin_relay)
			GPIO.setup(self.pin_relay_auto1, GPIO.OUT)
			GPIO.output(self.pin_relay_auto1, GPIO.HIGH)

		# Enable Relay Auto 2
		if self.relay_auto2_enabled():
			self._logger.info("Relay Automation 2 active on GPIO Pin [%s]"%self.pin_relay)
			GPIO.setup(self.pin_relay_auto2, GPIO.OUT)
			GPIO.output(self.pin_relay_auto2, GPIO.HIGH)

	def on_after_startup(self):
		self._logger.info("Filament and Relay Sensor Started")
		self._setup_sensor()
		while True:
			if self.on_printing():
				if self.relay_auto1_enabled():
					GPIO.output(self.pin_relay_auto1, GPIO.LOW)
					if self.relay_auto1_timeon_enabled():
						sleep(self.relay_auto1_timeon)
					if self.relay_auto1_timeout_enabled():
						GPIO.output(self.pin_relay_auto1, GPIO.HIGH)
						sleep(self.relay_auto1_timeout)

				if self.relay_auto2_enabled():
					GPIO.output(self.pin_relay_auto2, GPIO.LOW)
					if self.relay_auto2_timeon_enabled():
						sleep(self.relay_auto2_timeon)
					if self.relay_auto2_timeout_enabled():
						GPIO.output(self.pin_relay_auto2, GPIO.HIGH)
						sleep(self.relay_auto2_timeout)
			else:
				GPIO.cleanup( (self.pin_relay_auto1, self.pin_relay_auto2) )
				break

	def get_settings_defaults(self):
		return({
			'pin':'-1',   # Default is no pin
			'pin_relay_auto1':'-1',   # Default is no pin
			'pin_relay_auto2':'-1',   # Default is no pin
			'relay_auto1_timeon':'-1',   # Default is no pin
			'relay_auto1_timeout':'-1',   # Default is no pin
			'relay_auto2_timeon':'-1',   # Default is no pin
			'relay_auto2_timeout':'-1',   # Default is no pin
			'switch':0,	# Normally Open
			'pin_relay':'-1',   # Default is no pin
			'switch_pin_relay':0,	# Normally Open
			'poll_time':250,  # Debounce 250ms
			'confirmations':1,# Confirm that we're actually out of filament
			'no_filament_gcode':'M600',
			'gcode_relay':'M112',
			'debug_mode':0, # Debug off!
			'pause_print':False,
			'send_webhook':False,
			'ifttt_applet_name_pin1':'',
			'ifttt_applet_name_pin2':'',
			'ifttt_secretkey':''
		})
	
	def debug_only_output(self, string):
		if self.debug_mode==1:
			self._logger.info(string)

	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
		self._setup_sensor()

	def filament_sensor_enabled(self):
		return self.pin != '-1'

	def relay_sensor_enabled(self):
		return self.pin_relay != '-1'

	def relay_auto1_enabled(self):
		return self.pin_relay_auto1 != '-1'

	def relay_auto2_enabled(self):
		return self.pin_relay_auto2 != '-1'

	def relay_auto1_timeon_enabled(self):
		return self.relay_auto1_timeon != '-1'

	def relay_auto1_timeout_enabled(self):
		return self.relay_auto1_timeout != '-1'

	def relay_auto2_timeon_enabled(self):
		return self.relay_auto2_timeon != '-1'

	def relay_auto2_timeout_enabled(self):
		return self.relay_auto2_timeout != '-1'

	def no_filament(self):
		return GPIO.input(self.pin) == self.switch

	def on_printing(self):
		return self.print_started == True

	def relay_detected(self):
		return GPIO.input(self.pin_relay) == self.switch_pin_relay

	def get_assets(self):
		return dict(js=["js/filament_runout_for_orangepipc.js"])

	def get_template_configs(self):
		return [dict(type="settings", custom_bindings=False)]

	def on_event(self, event, payload):
		if event is Events.PRINT_STARTED:
			self.print_started = True
			if self.filament_sensor_enabled():
				self.debug_only_output("%s: Enabling Filament sensor." % (event))
				self._plugin_manager.send_plugin_message(self._identifier,
																	 dict(title="Filament Sensor", type="info", autoClose=True,
																		  msg="Enabling Filament Sensor."))
			if self.relay_sensor_enabled():
				self.debug_only_output("%s: Enabling Relay sensor." % (event))
				self._plugin_manager.send_plugin_message(self._identifier,
																	 dict(title="Relay Sensor", type="info", autoClose=True,
																		  msg="Enabling Relay Sensor."))
		elif event is Events.PRINT_RESUMED:
			# Prevent resume print when Filament Sensor is Triggered
			if self.filament_send_alert:
				self._plugin_manager.send_plugin_message(self._identifier,
																	 dict(title="Filament Sensor", type="error", autoClose=True,
																		  msg="Filament Sensor Triggered! Print paused."))
				self._printer.pause_print()
				self.print_started = False
			else:
				self.print_started = True
				self.filament_send_alert = False
			
			# Prevent resume print when Relay Sensor is Triggered
			if self.relay_send_alert:
				self._plugin_manager.send_plugin_message(self._identifier,
																	 dict(title="Relay Sensor", type="error", autoClose=True,
																		  msg="Relay Sensor Triggered! Print paused."))
				self._printer.pause_print()
				self.print_started = False
			else:
				self.print_started = True
				self.relay_send_alert = False

		# Disable sensor
		elif event in (
			Events.PRINT_DONE,
			Events.PRINT_FAILED,
			Events.PRINT_CANCELLED,
			Events.ERROR
		):
			self.debug_only_output("%s: Disabling filament sensor." % (event))
			self.print_started = False
			if self.relay_auto1_enabled():
				GPIO.output(self.pin_relay_auto1, GPIO.LOW)
			if self.relay_auto2_enabled():
				GPIO.output(self.pin_relay_auto2, GPIO.LOW)

		elif event is Events.PRINT_PAUSED:
			self.print_started = False

		elif event is Events.Z_CHANGE:
			if(self.print_started):	 
				# Set print_started to False to prevent that the starting command is called multiple times
				self.print_started = False		 

	@octoprint.plugin.BlueprintPlugin.route("/status", methods=["GET"])
	def check_status(self):
		status = "-1"
		if self.pin != '-1':
			status = str(self.no_filament())
		return jsonify( status = status )

	def filament_sensor_callback(self, _):
		while GPIO.input(self.pin) == self.switch:
			sleep(self.poll_time/1000)
			self.filament_send_alert_count+=1
			self.debug_only_output('Confirmations: '+str(self.filament_send_alert_count))
			if self.confirmations<=self.filament_send_alert_count:
				self.filament_send_alert = True
				self.filament_send_alert_count = 0
				self._logger.info("Filament Sensor Triggered!")
				self._plugin_manager.send_plugin_message(self._identifier,
																	 dict(title="Filament Sensor", type="error", autoClose=False,
																		  msg="No Filament Detected!"))
				if self.send_webhook:
					subprocess.Popen("curl -X POST -H 'Content-Type: application/json' https://maker.ifttt.com/trigger/%s/with/key/%s" % (self.ifttt_applet_name_pin1,self.ifttt_secretkey), shell=True)
					self.debug_only_output("Pin 1 Sending a webhook to ifttt.")
				if self.pause_print:
					self.debug_only_output("Pausing print.")
					self._printer.pause_print()
				if self.no_filament_gcode:
					self.debug_only_output("Sending Filament Sensor GCODE")
					self._printer.commands(self.no_filament_gcode)
				break
		else:
			self.filament_send_alert = False
			self.filament_send_alert_count = 0

	def relay_sensor_callback(self, _):
		while GPIO.input(self.pin_relay) == self.switch_pin_relay:
			self.relay_send_alert_count+=1
			self.debug_only_output('Confirmations: '+str(self.relay_send_alert_count))
			sleep(self.poll_time/1000)
			if self.confirmations<=self.relay_send_alert_count:
				self.relay_send_alert = True
				self.relay_send_alert_count = 0
				self._logger.info("Relay Sensor Triggered!")
				self._plugin_manager.send_plugin_message(self._identifier,
																	 dict(title="Relay Sensor", type="error", autoClose=False,
																		  msg="Relay Sensor Triggered!"))
				if self.send_webhook:
					subprocess.Popen("curl -X POST -H 'Content-Type: application/json' https://maker.ifttt.com/trigger/%s/with/key/%s" % (self.ifttt_applet_name_pin2,self.ifttt_secretkey), shell=True)
					self.debug_only_output("Pin 2 Sending a webhook to ifttt.")
				if self.pause_print:
					self.debug_only_output("Pausing print.")
					self._printer.pause_print()
				if self.gcode_relay:
					self.debug_only_output("Sending Relay Sensor GCODE")
					self._printer.commands(self.gcode_relay)
				break
		else:
			self.relay_send_alert = False
			self.relay_send_alert_count = 0

	def get_update_information(self):
		return dict(
			octoprint_filament_runout_for_orangepipc=dict(
				displayName="FilamentSensor OrangePiPc",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="NandoGommez",
				repo="Octoprint_FilamentSensor_for_OrangePiPc",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/NandoGommez/Octoprint_FilamentSensor_for_OrangePiPc/archive/{target_version}.zip"
			)
		)

__plugin_name__ = "FilamentSensor OrangePiPc"
__plugin_version__ = "2.1.41"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_check__():
	try:
		import OPi.GPIO as GPIO
	except ImportError:
		return False
	return True

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = FilamentSensorOrangePiPcPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}

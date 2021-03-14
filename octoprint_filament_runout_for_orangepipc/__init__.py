# coding=utf-8
from __future__ import absolute_import
from flask import jsonify

import octoprint.plugin
from octoprint.events import Events
import OPi.GPIO as GPIO
from time import sleep
import subprocess


class FilamentSensorOrangePiPcPlugin(octoprint.plugin.StartupPlugin,
                             octoprint.plugin.EventHandlerPlugin,
                             octoprint.plugin.TemplatePlugin,
                             octoprint.plugin.SettingsPlugin,
                             octoprint.plugin.RestartNeedingPlugin):

    def initialize(self):
        self._logger.info("Running OPi.GPIO")
        GPIO.setwarnings(False)        # Disable GPIO warnings
        self.FilamentSensorOrangePiPcPlugin_confirmations_tracking = 0

    @property
    def pin(self):
        return str(self._settings.get(["pin"]))

    @property
    def poll_time(self):
        return int(self._settings.get(["poll_time"]))

    @property
    def switch(self):
        return int(self._settings.get(["switch"]))

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
    def pause_print(self):
        return self._settings.get_boolean(["pause_print"])

    @property
    def send_webhook(self):
        return self._settings.get_boolean(["send_webhook"])

    @property
    def ifttt_applet_name(self):
        return str(self._settings.get(["ifttt_applet_name"]))

    @property
    def ifttt_secretkey(self):
        return str(self._settings.get(["ifttt_secretkey"]))

    def _setup_sensor(self):
        if self.sensor_enabled():
            self._logger.info("Using SUNXI Mode")
            GPIO.setmode(GPIO.SUNXI)
            self._logger.info("Filament Sensor active on GPIO Pin [%s]"%self.pin)
            GPIO.setup(self.pin, GPIO.IN, GPIO.HIGH)
        else:
            self._logger.info("Pin not configured, won't work unless configured!")

    def on_after_startup(self):
        self._logger.info("FilamentSensor-OrangePiPc started")
        self._setup_sensor()

    def get_settings_defaults(self):
        return({
            'pin':'-1',   # Default is no pin
            'poll_time':250,  # Debounce 250ms
            'switch':0,    # Normally Open
            'confirmations':5,# Confirm that we're actually out of filament
            'no_filament_gcode':'',
            'debug_mode':0, # Debug off!
            'pause_print':True,
            'send_webhook':False,
            'ifttt_applet_name':'',
            'ifttt_secretkey':''
        })
    
    def debug_only_output(self, string):
        if self.debug_mode==1:
            self._logger.info(string)

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._setup_sensor()

    def sensor_enabled(self):
        return self.pin != '-1'

    def no_filament(self):
        return GPIO.input(self.pin) != self.switch

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=False)]

    def on_event(self, event, payload):
        # Early abort in case of out ot filament when start printing, as we
        # can't change with a cold nozzle
        if event is Events.PRINT_STARTED and self.no_filament():
            self._logger.info("Printing aborted: no filament detected!")
            self._printer.cancel_print()
        # Enable sensor
        if event in (
            Events.PRINT_STARTED,
            Events.PRINT_RESUMED
        ):
            self._logger.info("%s: Enabling filament sensor." % (event))
            if self.sensor_enabled():
                GPIO.remove_event_detect(self.pin)
                GPIO.add_event_detect(
                    self.pin, GPIO.BOTH,
                    callback=self.sensor_callback,
                    bouncetime=self.poll_time
                )
        # Disable sensor
        elif event in (
            Events.PRINT_DONE,
            Events.PRINT_FAILED,
            Events.PRINT_CANCELLED,
            Events.ERROR
        ):
            self._logger.info("%s: Disabling filament sensor." % (event))
            GPIO.remove_event_detect(self.pin)

    @octoprint.plugin.BlueprintPlugin.route("/status", methods=["GET"])
    def check_status(self):
        status = "-1"
        if self.pin != '-1':
            status = str(self.no_filament())
        return jsonify( status = status )

    def sensor_callback(self, _):
        sleep(self.poll_time/1000)
        self.debug_only_output('Pin: '+str(GPIO.input(self.pin)))
        if self.no_filament():
            self.FilamentSensorOrangePiPcPlugin_confirmations_tracking+=1
            self.debug_only_output('Confirmations: '+str(self.FilamentSensorOrangePiPcPlugin_confirmations_tracking))
            if self.confirmations<=self.FilamentSensorOrangePiPcPlugin_confirmations_tracking:
                self._logger.info("Out of filament!")
                if self.send_webhook:
                subprocess.Popen("curl -X POST -H 'Content-Type: application/json' https://maker.ifttt.com/trigger/%s/with/key/%s" % (self.ifttt_applet_name,self.ifttt_secretkey), shell=True)
                self._logger.info("Sending a webhook to ifttt.")
                if self.pause_print:
                    self._logger.info("Pausing print.")
                    self._printer.pause_print()
                if self.no_filament_gcode:
                    self._logger.info("Sending out of filament GCODE")
                    self._printer.commands(self.no_filament_gcode)
                self.FilamentSensorOrangePiPcPlugin_confirmations_tracking = 0
        else:
            self.FilamentSensorOrangePiPcPlugin_confirmations_tracking = 0

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
                pip="https://github.com/NandoGommez/Octoprint_FilamentSensor_for_OrangePiPc/archive/master.zip"
            )
        )

__plugin_name__ = "FilamentSensor OrangePiPc"
__plugin_version__ = "2.0.7"
__plugin_pythoncompat__ = ">=2.7,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = FilamentSensorOrangePiPcPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}

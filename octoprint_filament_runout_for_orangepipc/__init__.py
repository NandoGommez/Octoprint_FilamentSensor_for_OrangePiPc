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
        GPIO.setwarnings(False)        # Disable GPIO warnings
        self.FilamentSensorOrangePiPcPlugin_confirmations_tracking = 0

    @property
    def pin(self):
        return str(self._settings.get(["pin"]))

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
        if self.sensor_enabled():
            self._logger.info("Using SUNXI Mode")
            GPIO.setmode(GPIO.SUNXI)
            self._logger.info("Filament Sensor active on GPIO Pin [%s]"%self.pin)
            GPIO.setup(self.pin, GPIO.IN)
        elif self.sensor_enabled_relay():
            self._logger.info("Using SUNXI Mode")
            GPIO.setmode(GPIO.SUNXI)
            self._logger.info("Relay Sensor active on GPIO Pin [%s]"%self.pin_relay)
            GPIO.setup(self.pin_relay, GPIO.IN)
        else:
            self._logger.info("No one Pin configured, won't work unless configured!")

    def on_after_startup(self):
        self._logger.info("FilamentSensor-OrangePiPc started")
        self._setup_sensor()

    def get_settings_defaults(self):
        return({
            'pin':'-1',   # Default is no pin
            'switch':0,    # Normally Open
            'pin_relay':'-1',   # Default is no pin
            'switch_pin_relay':0,    # Normally Open
            'poll_time':250,  # Debounce 250ms
            'confirmations':5,# Confirm that we're actually out of filament
            'no_filament_gcode':'',
            'gcode_relay':'M112',
            'debug_mode':0, # Debug off!
            'pause_print':True,
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

    def sensor_enabled(self):
        return self.pin != '-1'

    def sensor_enabled_relay(self):
        return self.pin_relay != '-1'

    def no_filament(self):
        return GPIO.input(self.pin) == self.switch

    def relay_detected(self):
        return GPIO.input(self.pin_relay) == self.switch_pin_relay

    def get_assets(self):
        return dict(js=["js/filament_runout_for_orangepipc.js"])

    def get_template_configs(self):
        return [dict(type="settings", custom_bindings=False)]

    def on_event(self, event, payload):
        # Early abort in case of out ot filament when start printing, as we
        # can't change with a cold nozzle
        if self.sensor_enabled():
            if event is Events.PRINT_STARTED and self.no_filament():
                self._logger.info("Printing aborted: no filament detected!")
                self._plugin_manager.send_plugin_message(self._identifier,
                                                                     dict(title="Filament Sensor", type="error", autoClose=True,
                                                                          msg="No filament detected! Print aborted."))
                self._printer.cancel_print()
            # Early pause in case of out ot filament when resume printing
            if event is Events.PRINT_RESUMED and self.no_filament():
                self._logger.info("Printing aborted: no filament detected!")
                self._plugin_manager.send_plugin_message(self._identifier,
                                                                     dict(title="Filament Sensor", type="error", autoClose=True,
                                                                          msg="No filament detected! Print paused."))
                self._printer.pause_print()
        # Enable sensor
        if event in (
            Events.PRINT_STARTED,
            Events.PRINT_RESUMED
        ):
            
            if self.sensor_enabled():
                self._logger.info("%s: Enabling Filament sensor." % (event))
                self._plugin_manager.send_plugin_message(self._identifier,
                                                                     dict(title="Filament Sensor", type="info", autoClose=True,
                                                                          msg="Enabling Filament Sensor."))
                GPIO.remove_event_detect(self.pin)
                GPIO.add_event_detect(
                    self.pin, GPIO.RISING,
                    callback=self.sensor_callback,
                    bouncetime=self.poll_time
                )
            if self.sensor_enabled_relay():
                self._logger.info("%s: Enabling Relay sensor." % (event))
                self._plugin_manager.send_plugin_message(self._identifier,
                                                                     dict(title="Relay Sensor", type="info", autoClose=True,
                                                                          msg="Enabling Relay Sensor."))
                GPIO.remove_event_detect(self.pin_relay)
                GPIO.add_event_detect(
                    self.pin_relay, GPIO.RISING,
                    callback=self.sensor_callback_relay,
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
                self._plugin_manager.send_plugin_message(self._identifier,
                                                                     dict(title="Filament Sensor", type="error", autoClose=False,
                                                                          msg="No Filament Detected! Print Paused."))
                if self.send_webhook:
                    subprocess.Popen("curl -X POST -H 'Content-Type: application/json' https://maker.ifttt.com/trigger/%s/with/key/%s" % (self.ifttt_applet_name_pin1,self.ifttt_secretkey), shell=True)
                    self._logger.info("Pin 1 Sending a webhook to ifttt.")
                if self.pause_print:
                    self._logger.info("Pausing print.")
                    self._printer.pause_print()
                if self.no_filament_gcode:
                    self._logger.info("Sending out of filament GCODE")
                    self._printer.commands(self.no_filament_gcode)
                self.FilamentSensorOrangePiPcPlugin_confirmations_tracking = 0
        else:
            self.FilamentSensorOrangePiPcPlugin_confirmations_tracking = 0
    
    def sensor_callback_relay(self, _):
        sleep(self.poll_time/1000)
        self.debug_only_output('Pin: '+str(GPIO.input(self.pin_relay)))
        if self.relay_detected():
            self._printer.commands(self.gcode_relay)
            self._plugin_manager.send_plugin_message(self._identifier,
                                                                     dict(title="Relay Sensor", type="error", autoClose=False,
                                                                          msg="Relay Sensor Triggered! Print Canceled."))
            if self.send_webhook:
                subprocess.Popen("curl -X POST -H 'Content-Type: application/json' https://maker.ifttt.com/trigger/%s/with/key/%s" % (self.ifttt_applet_name_pin2,self.ifttt_secretkey), shell=True)
                self._logger.info("Pin 2 Sending a webhook to ifttt.")
                

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
__plugin_version__ = "V2.0r"
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

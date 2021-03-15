$(function () {
    function filament_runout_for_orangepipcViewModel(parameters) {
        var self = this;

        self.validPinsBoard = [3,5,7,11,13,15,19,21,23,27,29,31,33,35,37,8,10,12,16,18,22,24,26,28,32,36,38,40];
        self.settingsViewModel = parameters[0];
        self.testSensorResult = ko.observable(null);
        self.gpio_mode_disabled = ko.observable(false);
        self.printing = ko.observable(false);
        self.gpio_mode_disabled_by_3rd = ko.computed(function() {
            return this.gpio_mode_disabled() && !this.printing();
        }, this);

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "filament_runout_for_orangepipc") {
                return;
            }

            new PNotify({
                title: 'Filament sensor simplified',
                text: data.msg,
                type: data.type,
                hide: data.autoClose
            });

        }

        self.testSensor = function () {
            // Cleanup
            $("#filament_runout_for_orangepipc_settings_testResult").removeClass("text-warning text-error text-info text-success");
            // Make api callback
            $.ajax({
                    url: "/api/plugin/filament_runout_for_orangepipc",
                    type: "post",
                    dataType: "json",
                    contentType: "application/json",
                    headers: {"X-Api-Key": UI_API_KEY},
                    data: JSON.stringify({
                        "command": "testSensor",
                        "pin": $("#filament_runout_for_orangepipc_settings_pinInput").val(),
                        "power": $("#filament_runout_for_orangepipc_settings_powerInput").val(),
                        "mode": $("#filament_runout_for_orangepipc_settings_gpioMode").val(),
                        "triggered": $("#filament_runout_for_orangepipc_settings_triggeredInput").val()
                    }),
                    statusCode: {
                        500: function () {
                            $("#filament_runout_for_orangepipc_settings_testResult").addClass("text-error");
                            self.testSensorResult('<i class="fas icon-warning-sign fa-exclamation-triangle"></i> OctoPrint experienced a problem. Check octoprint.log for further info.');
                        },
                        555: function () {
                            $("#filament_runout_for_orangepipc_settings_testResult").addClass("text-error");
                            self.testSensorResult('<i class="fas icon-warning-sign fa-exclamation-triangle"></i> This pin is already in use, choose other pin.');
                        },
                        556: function () {
                            $("#filament_runout_for_orangepipc_settings_testResult").addClass("text-error");
                            self.testSensorResult('<i class="fas icon-warning-sign fa-exclamation-triangle"></i> The pin selected is power, ground or out of range pin number, choose other pin');
                        }
                    },
                    error: function () {
                        $("#filament_runout_for_orangepipc_settings_testResult").addClass("text-error");
                        self.testSensorResult('<i class="fas icon-warning-sign fa-exclamation-triangle"></i> There was an error :(');
                    },
                    success: function (result) {
                        // triggered when open
                        if ($("#filament_runout_for_orangepipc_settings_triggeredInput").val() === "0") {
                            if (result.triggered === true) {
                                $("#filament_runout_for_orangepipc_settings_testResult").addClass("text-success");
                                self.testSensorResult('<i class="fas icon-ok fa-check"></i> Sensor detected filament!');
                            } else {
                                $("#filament_runout_for_orangepipc_settings_testResult").addClass("text-info");
                                self.testSensorResult('<i class="icon-stop"></i> Sensor triggered!')
                            }
                        // triggered when closed
                        } else {
                            if (result.triggered === true) {
                                $("#filament_runout_for_orangepipc_settings_testResult").addClass("text-success");
                                self.testSensorResult('<i class="fas icon-ok fa-check"></i> Sensor triggered!');
                            } else {
                                $("#filament_runout_for_orangepipc_settings_testResult").addClass("text-info");
                                self.testSensorResult('<i class="icon-stop"></i> Sensor detected filament or not working!')
                            }
                        }
                    }
                }
            );
        }
        self.checkWarningPullUp = function(event){
            // Which mode are we using
            var mode = parseInt($('#filament_runout_for_orangepipc_settings_gpioMode').val(),10);
            // What pin is the sensor connected to
            var pin = parseInt($('#filament_runout_for_orangepipc_settings_pinInput').val(),10);
            // What is the sensor connected to - ground or 3.3v
            var sensorCon = parseInt($('#filament_runout_for_orangepipc_settings_powerInput').val(),10);

            // Show alerts
            if (
                sensorCon == 1 && (
                    (mode == 10 && (pin==3 || pin == 5))
                    ||
                    (mode == 11 && (pin == 2 || pin == 3))
                )
            ){
                $('#filament_runout_for_orangepipc_settings_pullupwarn').removeClass('hidden pulsAlert').addClass('pulsAlert');
            }else{
                $('#filament_runout_for_orangepipc_settings_pullupwarn').addClass('hidden').removeClass('pulsAlert');
            }

            // Set max to right board type - 10 = Boardmode
            var showWarning = true;
            if (mode == 10){
                $('#filament_runout_for_orangepipc_settings_pinInput').attr('max',40);
                if (pin != 0 && $.inArray(pin,self.validPinsBoard) == -1){
                    showWarning = false;
                    $('#filament_runout_for_orangepipc_settings_badpin').removeClass('hidden pulsAlert').addClass('pulsAlert');
                }else{
                    $('#filament_runout_for_orangepipc_settings_badpin').addClass('hidden').removeClass('pulsAlert');
                }
            }else{
                $('#filament_runout_for_orangepipc_settings_pinInput').attr('max',27);
            }

            // High or low
            if ($('#filament_runout_for_orangepipc_settings_pinInput').attr('max') < pin || pin < 0){
                $('#filament_runout_for_orangepipc_settings_badpin').removeClass('hidden pulsAlert').addClass('pulsAlert');
            }else{
                // If the warning is not already shown then show it now
                if (showWarning){
                    $('#filament_runout_for_orangepipc_settings_badpin').addClass('hidden').removeClass('pulsAlert');
                }
            }
        }

        self.getDisabled = function (item) {
            $.ajax({
                type: "GET",
                dataType: "json",
                url: "plugin/filament_runout_for_orangepipc/disable",
                success: function (result) {
                    self.gpio_mode_disabled(result.gpio_mode_disabled)
                    self.printing(result.printing)
                }
            });
        };

        self.onSettingsShown = function () {
            self.testSensorResult("");
            self.getDisabled();
             // Check for broken settings
            $('#filament_runout_for_orangepipc_settings_gpioMode, #filament_runout_for_orangepipc_settings_pinInput, #filament_runout_for_orangepipc_settings_powerInput').off('change.fsensor').on('change.fsensor',self.checkWarningPullUp);
            $('#filament_runout_for_orangepipc_settings_gpioMode').trigger('change.fsensor');
        }
    }

    // This is how our plugin registers itself with the application, by adding some configuration
    // information to the global variable OCTOPRINT_VIEWMODELS
    ADDITIONAL_VIEWMODELS.push({
        construct: filament_runout_for_orangepipcViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["#settings_plugin_filament_runout_for_orangepipc"]
    })
})

$(function () {
    function filament_runout_for_orangepipcViewModel(parameters) {

        self.onDataUpdaterPluginMessage = function (plugin, data) {
            if (plugin !== "filament_runout_for_orangepipc") {
                return;
            }

            new PNotify({
                title: 'FilamentSensor OrangePiPc',
                text: data.msg,
                type: data.type,
                hide: data.autoClose
            });

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

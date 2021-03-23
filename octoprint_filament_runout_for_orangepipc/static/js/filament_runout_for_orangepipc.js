$(function() {
    function filament_runout_for_orangepipcViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "filament_runout_for_orangepipc") {
                return;
            }

            new PNotify({
                title: data.title,
                text: data.msg,
                type: data.type,
                hide: data.autoClose
            });
        }
    }

    ADDITIONAL_VIEWMODELS.push([
        filament_runout_for_orangepipcViewModel,

        // This is a list of dependencies to inject into the plugin, the order which you request
        // here is the order in which the dependencies will be injected into your view model upon
        // instantiation via the parameters argument
        [],

        // Finally, this is the list of selectors for all elements we want this view model to be bound to.
        []
    ]);
});

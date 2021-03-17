$(function() {
    function filament_runout_for_orangepipcViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0];

        self.isFilamentOn = ko.observable(undefined);
        self.filamentstats_indicator = $("#filament_indicator");

        self.onStartup = function () {
            self.isFilamentOn.subscribe(function() {
                if (self.isFilamentOn()) {
                    self.filamentstats_indicator.removeClass("off").addClass("on");
                } else {
                    self.filamentstats_indicator.removeClass("on").addClass("off");
                }   
            });

            $.ajax({
                url: API_BASEURL + "plugin/ilament_runout_for_orangepipc",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "getFilamentState"
                }),
                contentType: "application/json; charset=UTF-8"
            }).done(function(data) {
                self.isFilamentOn(data.isFilamentOn);
            });

        }

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "filament_runout_for_orangepipc") {
                return;
            }

            if (data.isFilamentOn !== undefined) {
                self.isFilamentOn(data.isFilamentOn);
            } else {

            new PNotify({
                title: 'FilamentSensor OrangePiPc',
                text: data.msg,
                type: data.type,
                hide: data.autoClose
            });
            }
        }
    
    }

    ADDITIONAL_VIEWMODELS.push([
        filament_runout_for_orangepipcViewModel,

        // This is a list of dependencies to inject into the plugin, the order which you request
        // here is the order in which the dependencies will be injected into your view model upon
        // instantiation via the parameters argument
        [],

        // Finally, this is the list of selectors for all elements we want this view model to be bound to.
        ["#navbar_plugin_filament_runout_for_orangepipc"]
    ]);
});

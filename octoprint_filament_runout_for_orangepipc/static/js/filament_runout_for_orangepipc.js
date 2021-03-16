$(function() {
    function filament_runout_for_orangepipcViewModel(parameters) {
        var self = this;

        self.settingsViewModel = parameters[0]
        self.loginState = parameters[1];
        
        self.settings = undefined;

        self.isFilament = ko.observable(undefined);

        self.filamenticon_indicator = $("#filamentsensor_indicator");


        self.onStartup = function () {
            self.isFilament.subscribe(function() {
                if (data.isFilament == 1) {
                    self.filamenticon_indicator.removeClass("no").addClass("yes");
                } else {
                    self.filamenticon_indicator.removeClass("yes").addClass("no");
                }   
            });
            
            $.ajax({
                url: API_BASEURL + "plugin/filament_runout_for_orangepipc",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "getFilamentState"
                }),
                contentType: "application/json; charset=UTF-8"
            }).done(function(data) {
                self.isFilament(data.isFilament);
            });
        }

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "filament_runout_for_orangepipc") {
                return;
            }

            if (data.isFilament !== undefined) {
                self.isFilament(data.isFilament);
            }
        };

           
    }

    ADDITIONAL_VIEWMODELS.push([
        filament_runout_for_orangepipcViewModel,
        ["settingsViewModel", "loginStateViewModel"],
        ["#navbar_plugin_filament_runout_for_orangepipc", "#settings_plugin_filament_runout_for_orangepipc"]
    ]);
});

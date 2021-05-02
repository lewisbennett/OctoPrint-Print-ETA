$(function() {

    class ETAViewModel {

        constructor(parameters) {

            var self = this;

            self.settings = parameters[0];

            // Assign default value until the plugin sends us an update.
            self.eta = ko.observable("-");

            self.onBeforeBinding = function () {

                var element = $("#state").find(".accordion-inner .progress");

                if (element.length)
                    element.before(gettext("ETA") + ": <strong id='eta_string' data-bind=\"html: eta\"></strong><br>");
            };

            self.onDataUpdaterPluginMessage = function (plugin, data) {
                
                if (plugin == "print_eta")
                    self.eta(data.eta_string);
            };
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        
        construct: ETAViewModel,
        dependencies: ["printerStateViewModel", "settingsViewModel"],
        elements: ["#eta_string"]
    });
});
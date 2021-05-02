from __future__ import absolute_import, unicode_literals
from octoprint.util import RepeatedTimer
from babel.dates import format_date, format_datetime, format_time

import octoprint.plugin
import time
import datetime

class PrintETAPlugin(octoprint.plugin.AssetPlugin, octoprint.plugin.EventHandlerPlugin, octoprint.plugin.ProgressPlugin, octoprint.plugin.SettingsPlugin, octoprint.plugin.StartupPlugin):

    # Initialize the plugin.
    def __init__(self):

        self.eta_string = "-"

        # Used to compare ETA strings before pushing them to the UI, or the printer.
        global previous_eta_string
        previous_eta_string = ""

        global CustomTimeFormat
        CustomTimeFormat = "HH:mm:ss"

    # Defines the static assets the plugin offers.
    def get_assets(self):

        self._logger.debug("get_assets called.")

        return dict(
            js = ["js/print_eta.js"]
        )

    # Retrieves the plugin’s default settings with which the plugin’s settings manager will be initialized.
    def get_settings_defaults(self):

        self._logger.debug("get_settings_defaults called.")

        return dict(

            # Controls whether to show time in 24 hour view (13:00), or 12 hour view (1:00 PM).
            use_twenty_four_hour = True
        )

    # Called just after launch of the server, so when the listen loop is actually running already.
    def on_after_startup(self):
        self._logger.debug("on_after_startup called.")

    # Called by OctoPrint upon processing of a fired event on the platform.
    # event (string) - The type of event that got fired, see the list of events for possible values: https://docs.octoprint.org/en/master/events/index.html#sec-events-available-events
    # payload (dictionary) - The payload as provided with the event
    def on_event(self, event, payload):

        self._logger.debug("on_event called.")

        if event in ["PrintStarted", "PrintResumed"]:
            self.refresh_eta()

    # Called by OctoPrint on minimally 1% increments during a running print job.
    # storage (string) - Location of the file
    # path (string) - Path of the file
    # progress (int) - Current progress as a value between 0 and 100
    def on_print_progress(self, storage, path, progress):

        self._logger.debug("on_print_progress called.")

        self.refresh_eta()

    # Calculates the current print's ETA.
    def calculate_eta(self):

        self._logger.debug("calculate_eta called.")

        current_data = self._printer.get_current_data()

        if "progress" not in current_data:
            return "N/A"

        progress_data = current_data["progress"]

        if "printTimeLeft" not in progress_data:
            return "N/A"
        
        print_time_left = progress_data["printTimeLeft"]

        # If the print hasn't begun yet, "printTimeLeft" won't have a type.
        if type(print_time_left) != int:
            return "N/A"

        current_time = datetime.datetime.today()

        print_finish_time = current_time + datetime.timedelta(0, print_time_left)

        str_time = format_time(print_finish_time, CustomTimeFormat)

        self._logger.debug("str_time: " + str_time)

        str_date = ""

        if print_finish_time.day > current_time.day:

            if print_finish_time.day == current_time.day + 1:
                str_date = "Tomorrow"

            else:
                str_time = " " + format_date(print_finish_time, "EEE d")

        self._logger.debug("str_date: " + str_date)
        self._logger.debug(str_time + str_date)

        return str_time + str_date

     # Refreshes the ETA on the UI, if required.
    
    # Refreshes the ETA on the UI, if required.
    def refresh_eta(self):

        self._logger.debug("refresh_eta called.")

        self.eta_string = self.calculate_eta()

        global previous_eta_string

        # Compare the new and previous ETA string before pushing any updates to the UI or printer.
        if (self.eta_string != previous_eta_string):

            previous_eta_string = self.eta_string

            # Notify listeners of new ETA string value.
            self._plugin_manager.send_plugin_message(self._identifier, dict(eta_string = self.eta_string))

__plugin_name__ = "Print ETA"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = PrintETAPlugin()
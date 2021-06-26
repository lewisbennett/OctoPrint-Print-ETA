from __future__ import absolute_import, unicode_literals
import logging
from octoprint.util import RepeatedTimer
from babel.dates import format_date, format_time

import octoprint.plugin
import datetime

class PrintETAPlugin(octoprint.plugin.AssetPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.ProgressPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin):

    # Initialize the plugin.
    def __init__(self):

        self.logger = logging.getLogger("octoprint.plugins.print_eta")

        self.eta_string = "-"
        self.printer_message = ""
        self.has_started_up = False

        # Used to compare ETA strings before pushing them to the UI.
        global previous_eta_string
        previous_eta_string = ""

        # Used to compare printer messages before pushing them to the printer.
        global previous_printer_message
        previous_printer_message = ""

        # Used to determine the message that should be calculated.
        # 0: ETA message.
        # 1: Time elapsed message.
        # 2: Time remaining message.
        # 3: Progress percentage message.
        global message_mode
        message_mode = 0

    # Defines the static assets the plugin offers.
    def get_assets(self):

        self.logger.debug("get_assets called.")

        return dict(
            js = ["js/print_eta.js"]
        )

    # Retrieves the plugin’s default settings with which the plugin’s settings manager will be initialized.
    def get_settings_defaults(self):

        self.logger.debug("get_settings_defaults called.")

        return dict(

            # Whether to show time in 24 hour view (13:00), or 12 hour view (1:00 PM).
            use_twenty_four_hour_view = True,

            # Whether to use "fancy" text (e.g. Tomorrow).
            use_fancy_text = True,

            # Whether to send the ETA to the printer via an M117 command.
            show_eta_on_printer = True,

            # Whether to remove colons from ETA strings (required for some printer firmwares).
            remove_colons = False,

            # Whether to enable message cycling on the printer's screen, if enabled.
            enable_message_cycling = True,

            # Whether to include the ETA message within the message cycle, if enabled.
            message_cycle_eta_message = True,

            # Whether to include the time elapsed message within the message cycle, if enabled.
            message_cycle_time_elapsed_message = True,

            # Whether to include the time remaining message within the message cycle, if enabled.
            message_cycle_time_remaining_message = True,

            # Whether to include the progress percentage message within the message cycle, if enabled.
            message_cycle_progress_percentage = True,

            # The interval between messages included in the message cycle.
            message_cycle_interval_minutes = 1
        )

    # Allows configuration of injected navbar, sidebar, tab and settings templates.
    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=False),
            dict(type="settings", custom_bindings=False)
        ]

    # Gets the latest plugin version information.
    def get_update_information(self):
        return dict(
            display_eta=dict(
                displayName=self._plugin_name,
                displayVersion=self._plugin_version,
                type="github_release",
                current=self._plugin_version,
                user="lewisbennett",
                repo="Octoprint-Print-ETA",
                pip="https://github.com/lewisbennett/Octoprint-Print-ETA/archive/{target}.zip"
            )
        )

    # Called just after launch of the server, so when the listen loop is actually running already.
    def on_after_startup(self):

        self.logger.debug("on_after_startup called.")

        # Get settings.
        global remove_colons
        remove_colons = self._settings.get(["remove_colons"])

        global show_eta_on_printer
        show_eta_on_printer = self._settings.get(["show_eta_on_printer"])

        global use_fancy_text
        use_fancy_text = self._settings.get(["use_fancy_text"])

        global use_twenty_four_hour_view
        use_twenty_four_hour_view = self._settings.get(["use_twenty_four_hour_view"])

        global enable_message_cycling
        enable_message_cycling = self._settings.get(["enable_message_cycling"])

        global message_cycle_eta_message
        message_cycle_eta_message = self._settings.get(["message_cycle_eta_message"])

        global message_cycle_time_elapsed_message
        message_cycle_time_elapsed_message = self._settings.get(["message_cycle_time_elapsed_message"])

        global message_cycle_time_remaining_message
        message_cycle_time_remaining_message = self._settings.get(["message_cycle_time_remaining_message"])

        global message_cycle_progress_percentage
        message_cycle_progress_percentage = self._settings.get(["message_cycle_progress_percentage"])

        global message_cycle_interval_minutes
        message_cycle_interval_minutes = self._settings.get(["message_cycle_interval_minutes"])

        # Get the initial message mode.
        global message_mode

        # If the ETA message is disabled in the cycle, calculate the correct starting mode.
        if not message_cycle_eta_message:
            message_mode = self.get_next_message_mode()

        # Set up a timer for message cycling, if enabled.
        self.timer = RepeatedTimer(message_cycle_interval_minutes * 60, PrintETAPlugin.on_timer_elapsed, args=[self])

        self.has_started_up = True

    # Called by OctoPrint upon processing of a fired event on the platform.
    # event (string) - The type of event that got fired, see the list of events for possible values: https://docs.octoprint.org/en/master/events/index.html#sec-events-available-events
    # payload (dictionary) - The payload as provided with the event
    def on_event(self, event, payload):

        self.logger.debug("on_event called ({}).".format(event))

        if not self.has_started_up:
            return

        # Only recalculate the ETA if the event is a print related event.
        # ClientOpened - event when OctoPrint starts being viewed (allows us to calculate the ETA quickly after refreshing OctoPrint, or opening from another device mid-print).
        # FileRemoved - event when a file is removed from OctoPrint's storage (allows the ETA to be cleared if the active print file is removed).
        # Print* - react to all print related events.
        if event.startswith("Print") or event in ["ClientOpened", "FileRemoved"]:

            # Events to start the timer.
            if event in ["PrintStarted", "PrintResumed"]:

                global enable_message_cycling

                if enable_message_cycling:
                    self.timer.start()

            # Events to cancel the timer.
            elif event in ["PrintDone", "PrintCancelled", "PrintFailed", "PrintPaused"]:
                self.timer.cancel()

            self.refresh_messages()

    # Called by OctoPrint on minimally 1% increments during a running print job.
    # storage (string) - Location of the file
    # path (string) - Path of the file
    # progress (int) - Current progress as a value between 0 and 100
    def on_print_progress(self, storage, path, progress):

        self.logger.debug("on_print_progress called.")

        if self.has_started_up:
            self.refresh_messages()

    # Calculates the required messages based on the printer's current state.
    def calculate_messages(self):

        self.logger.debug("calculate_messages called.")

        # Get the printer's current data, and validate that it's in a state where we can calculate the ETA.
        current_data = self._printer.get_current_data()

        if "progress" not in current_data:
            return "-"

        progress_data = current_data["progress"]

        if "printTimeLeft" not in progress_data:
            return "-"
        
        print_time_left = progress_data["printTimeLeft"]

        # If the print hasn't begun yet, "printTimeLeft" won't have a type.
        if type(print_time_left) != int:
            return "-"

        # We have all the information we need to calculate the ETA by this point.

        global use_fancy_text
        global use_twenty_four_hour_view

        current_time = datetime.datetime.today()

        print_time_remaining = datetime.timedelta(0, print_time_left)

        print_finish_time = current_time + print_time_remaining

        eta_string = ""

        if use_twenty_four_hour_view:
            eta_string = format_time(print_finish_time, "HH:mm:ss")

        else:
            eta_string = format_time(print_finish_time, "hh:mm:ss a")

        # Append the ETA string with the date, if the print is not due to finish today.
        if (print_finish_time.day > current_time.day):

            if print_finish_time.day == current_time.day + 1 and use_fancy_text:
                eta_string += " tomorrow"

            else:
                eta_string += format_date(print_finish_time, "EEE d")

        # End of ETA string calculation.
        self.eta_string = eta_string

        global enable_message_cycling

        global message_mode

        if enable_message_cycling and message_mode != 0:

            new_printer_message = ""

            # Time elapsed message.
            if message_mode == 1:

                print_time_elapsed = progress_data["printTime"]

                if type(print_time_elapsed) == int:
                    new_printer_message = "Elapsed: " + self.get_time_string(datetime.timedelta(0, print_time_elapsed))

            # Time remaining message.
            elif message_mode == 2:
                new_printer_message = "Remaining: " + self.get_time_string(print_time_remaining)

            # Progress percentage message.
            elif message_mode == 3:
                
                completion = progress_data["completion"]

                if type(completion) == float:

                    self.logger.debug("Print completion: " + str(completion))

                    new_printer_message = str(int(completion)) + "% complete"

            self.printer_message = new_printer_message

        else:
            self.printer_message = "ETA: {}".format(eta_string)

    # Gets the next message mode.
    def get_next_message_mode(self):

        self.logger.debug("get_next_message_mode called.")

        messages = []

        global message_cycle_eta_message

        if message_cycle_eta_message:
            messages.append(0)

        global message_cycle_time_elapsed_message

        if message_cycle_time_elapsed_message:
            messages.append(1)

        global message_cycle_time_remaining_message

        if message_cycle_time_remaining_message:
            messages.append(2)

        global message_cycle_progress_percentage

        if message_cycle_progress_percentage:
            messages.append(3)

        # Return -1 if all messages are disabled.
        if len(messages) == 0:
            return -1

        # We want to find the next message mode. This will either be the first item in the collection,
        # or the next item with a greater value. If a greater value is found, use that and break the
        # loop. Otherwise, the loop will finish and the initial value will be used, restarting the cycle.
        new_message_mode = messages[0]

        global message_mode

        for message in messages:

            if message > message_mode:

                new_message_mode = message

                break

        self.logger.debug("New message mode: " + str(new_message_mode))

        return new_message_mode

    # Gets a datetime object as a human-readable string (e.g. 1 day, 2 hours, 3 minutes)
    # datetime (timedelta) - The time delta to calculate the string for.
    def get_time_string(self, timedelta):
        
        self.logger.debug("get_time_string called.")

        message = []

        # Add days, if needed.
        if timedelta.days > 0:
            message.append("{}d".format(timedelta.days))

        hours = timedelta.seconds // 3600

        # Add hours, if needed.
        if hours > 0:
            message.append("{}h".format(hours))

        minutes = (timedelta.seconds // 60) % 60

        # Add minutes, if needed.
        if minutes > 0:
            message.append("{}m".format(minutes))

        seconds = (timedelta.seconds // 3600) % 60

        if seconds > 0:
            message.append("{}s".format(seconds))

        return ", ".join(message)

    # Event handler for timer to handle message mode switching.
    def on_timer_elapsed(self):

        self.logger.debug("on_timer_elapsed called.")

        global enable_message_cycling

        # Make sure that message cycling is enabled before moving to the next mode.
        if enable_message_cycling:

            global message_mode

            message_mode = self.get_next_message_mode()

            self.refresh_messages()

    # Refreshes the messages being shown to the user.
    def refresh_messages(self):

        self.logger.debug("refresh_messages called.")

        self.calculate_messages()

        self.logger.debug("ETA string: " + self.eta_string)
        self.logger.debug("Printer message: " + self.printer_message)

        global previous_eta_string

        # Compare the new and previous ETA string before pushing any updates to the UI.
        if self.eta_string != previous_eta_string:

            previous_eta_string = self.eta_string

            # Notify listeners of new ETA string value.
            self._plugin_manager.send_plugin_message(self._identifier, dict(eta_string = self.eta_string))

        global show_eta_on_printer

        # Send M117 command to printer, if setting is enabled.
        if show_eta_on_printer:

            global previous_printer_message

            if not str.isspace(self.printer_message) and self.printer_message != previous_printer_message:

                previous_printer_message = self.printer_message

                message = self.printer_message

                global remove_colons

                # Remove colons, if enabled. 
                if remove_colons:
                    message = message.replace(":", "")

                self._printer.commands("M117 {}".format(message))

__plugin_name__ = "Print ETA"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = PrintETAPlugin()

__plugin_hooks__ = {
    "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}
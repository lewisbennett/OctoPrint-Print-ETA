from __future__ import absolute_import, unicode_literals
import logging
from babel.dates import format_date, format_time

from octoprint.events import Events
from octoprint.util import RepeatedTimer

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

        # The ETA string passed to the OctoPrint UI.
        self.eta_string = "-"

        # The message string passed to the printer, if enabled.
        self.printer_message = ""

        # Whether the plugin has properly started up. Prevents issues as a result of trying to calculate messages too early.
        self.has_started_up = False

        # Used to compare ETA strings before pushing them to the UI.
        self.previous_eta_string = ""

        # Used to compare printer messages before pushing them to the printer.
        self.previous_printer_message = ""

        # Will be used for the timer for printer messages.
        self.timer = None

        # Used to determine the message that should be calculated.
        # 0: ETA message.
        # 1: Time elapsed message.
        # 2: Time remaining message.
        # 3: Progress percentage message.
        self.printer_message_mode = 0

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

            # Whether to update the progress bar on the printer via an M73 command.
            show_progress_on_printer = True,

            # Whether to remove colons from ETA strings (required for some printer firmwares).
            remove_colons = False,

            # Whether to enable messages on the printer's screen.
            enable_printer_messages = True,

            # Whether to show the print's ETA on the printer's screen.
            show_eta_printer_message = True,

            # Whether to show how long the print has been running for on the printer's screen.
            show_time_elapsed_printer_message = True,

            # Whether to show how long the print has left on the printer's screen.
            show_time_remaining_printer_message = True,

            # Whether to show the print's progress on the printer's screen.
            show_progress_printer_message = False,

            # The interval between printer messages.
            printer_message_interval = 10
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

        # Get general settings.
        self.setting_show_progress_on_printer = self._settings.get(["show_progress_on_printer"])
        self.setting_use_twenty_four_hour_view = self._settings.get(["use_twenty_four_hour_view"])

        # Get formatting settings.
        self.setting_remove_colons = self._settings.get(["remove_colons"])

        # Get printer message settings.
        self.setting_enable_printer_messages = self._settings.get(["enable_printer_messages"])
        self.setting_show_eta_printer_message = self._settings.get(["show_eta_printer_message"])
        self.setting_show_time_elapsed_printer_message = self._settings.get(["show_time_elapsed_printer_message"])
        self.setting_show_time_remaining_printer_message = self._settings.get(["show_time_remaining_printer_message"])
        self.setting_show_progress_printer_message = self._settings.get(["show_progress_printer_message"])
        self.setting_printer_message_interval = self._settings.get(["printer_message_interval"])

        # Previously, the interval was set in minutes however, if you're looking for information at a glance,
        # this may be too long a period. This setting was changed on 20/09/2021.
        if self.setting_printer_message_interval < 10:
            self.setting_printer_message_interval = 10;

        # If the ETA message is disabled in the cycle, calculate the correct starting mode.
        if not self.setting_show_eta_printer_message:
            self.printer_message_mode = self.get_next_printer_message_mode()

        self.has_started_up = True

    # Called by OctoPrint upon processing of a fired event on the platform.
    # event (string) - The type of event that got fired, see the list of events for possible values: https://docs.octoprint.org/en/master/events/index.html#sec-events-available-events
    # payload (dictionary) - The payload as provided with the event
    def on_event(self, event, payload):

        self.logger.debug("on_event called ({}).".format(event))

        if not self.has_started_up:
            return

        # Show the latest ETA message when the webpage loads.
        if event == Events.CLIENT_OPENED:

            self.dispatch_eta_message()

            return

        if self._printer.is_printing():

            # Event filter when printing.
            if not event.startswith("Print"):
                return

            if self.setting_enable_printer_messages and type(self.timer) != RepeatedTimer:

                self.timer = RepeatedTimer(self.setting_printer_message_interval, PrintETAPlugin.on_timer_elapsed, args=[self])

                self.timer.start()

        else:

            # Event filter while printer is idle.
            if not event.startswith("Print") and event not in [Events.FILE_REMOVED]:
                return

            if type(self.timer) == RepeatedTimer:

                self.timer.cancel()

                self.timer = None

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

        # Can't proceed without progress data.
        if "progress" not in current_data:

            self.eta_string = "-"
            self.printer_message = ""
            
            return

        progress_data = current_data["progress"]

        # Can't calculate ETA without knowing how long the print has left.
        if "printTimeLeft" not in progress_data:

            self.eta_string = "-"
            self.printer_message = ""
            
            return
        
        print_time_left = progress_data["printTimeLeft"]

        # If the print hasn't begun yet, "printTimeLeft" won't have a type.
        if type(print_time_left) != int:

            self.eta_string = "-"
            self.printer_message = ""

            return

        # We have all the information we need to calculate the ETA by this point.

        current_time = datetime.datetime.today()

        print_time_remaining = datetime.timedelta(0, print_time_left)

        # This is the actual ETA. We'll use this to calculate a string based on the user's preferences.
        print_finish_time = current_time + print_time_remaining

        eta_string = None

        if self.setting_use_twenty_four_hour_view:
            eta_string = format_time(print_finish_time, "HH:mm:ss")

        else:
            eta_string = format_time(print_finish_time, "hh:mm:ss a")

        # Append the ETA string with the date, if the print is not due to finish today.
        if (print_finish_time.day > current_time.day):

            # Check if the print is due to finish tomorrow
            if print_finish_time.date() == current_time.date() + datetime.timedelta(days=1):
                eta_string += " tomorrow"

            else:
                eta_string += " " + format_date(print_finish_time, "EEE d")

        # End of ETA string calculation.
        self.eta_string = eta_string

        # Begin printer message calculation.

        completion = None

        print_time_elapsed = progress_data["printTime"]

        # If we were able to get the time elapsed successfully, calculate a more accurate progress than the 'completion' value.
        # This allows the plugin to show a more accurate percentage if plugins such as PrintTimeGenius are present.
        # Total print duration = print time elapsed + print time remaining
        # Percentage completion = (print time elapsed / total print duration) * 100
        if type(print_time_elapsed) == int:
            completion = (print_time_elapsed / (print_time_elapsed + print_time_left)) * 100.0

        # Use the system provided completion as a fallback.
        else:
            completion = progress_data["completion"]

        # Send the progress to the printer, if enabled.
        if type(completion) == float and self.setting_show_progress_on_printer:

            self._printer.commands("M73 P{}".format(int(completion)))

            self.logger.debug("Sent M73")

        # If message cycling is enabled, check that the mode isn't zero, as this represents the ETA string,
        # and we can re-use the ETA string from above instead of calculating a new one.
        if self.setting_enable_printer_messages and self.printer_message_mode != 0:

            new_printer_message = ""

            # Time elapsed message.
            if self.printer_message_mode == 1:

                if type(print_time_elapsed) == int:
                    new_printer_message = "Elapsed: " + self.get_time_string(datetime.timedelta(0, print_time_elapsed))

            # Time remaining message.
            elif self.printer_message_mode == 2:
                new_printer_message = "Remaining: " + self.get_time_string(print_time_remaining)

            # Progress percentage message.
            elif self.printer_message_mode == 3:
                
                if type(completion) == float:

                    self.logger.debug("Print completion: " + str(completion))

                    new_printer_message = str(int(completion)) + "% complete"

            self.printer_message = new_printer_message

        else:
            self.printer_message = "ETA: {}".format(eta_string)

    # Gets the next message mode.
    def get_next_printer_message_mode(self):

        self.logger.debug("get_next_printer_message_mode called.")

        messages = []

        if self.setting_show_eta_printer_message:
            messages.append(0)

        if self.setting_show_time_elapsed_printer_message:
            messages.append(1)

        if self.setting_show_time_remaining_printer_message:
            messages.append(2)

        if self.setting_show_progress_printer_message:
            messages.append(3)

        # Return -1 if all messages are disabled.
        if len(messages) == 0:
            return -1

        # We want to find the next message mode. This will either be the first item in the collection,
        # or the next item with a greater value. If a greater value is found, use that and break the
        # loop. Otherwise, the loop will finish and the initial value will be used, restarting the cycle.
        new_printer_message_mode = messages[0]

        for message in messages:

            if message > self.printer_message_mode:

                new_printer_message_mode = message

                break

        self.logger.debug("New message mode: " + str(new_printer_message_mode))

        return new_printer_message_mode

    # Gets a datetime object as a human-readable string (e.g. 1 day, 2 hours, 3 minutes)
    # datetime (timedelta) - The time delta to calculate the string for.
    def get_time_string(self, timedelta):
        
        self.logger.debug("get_time_string called.")

        hours = timedelta.seconds // 3600
        minutes = (timedelta.seconds // 60) % 60
        seconds = (timedelta.seconds // 3600) % 60

        # Format the hours, minutes and seconds to have prefixing zeroes when only single digits.
        message = f'{hours:02d}' + ":" + f'{minutes:02d}' + ":" + f'{seconds:02d}'

        # Insert the number of days left if greater than zero.
        if timedelta.days > 0:
            message = "{}d".format(timedelta.days) + " " + message

        return message

    # Event handler for timer to handle message mode switching.
    def on_timer_elapsed(self):

        self.logger.debug("on_timer_elapsed called.")

        # Make sure that printer messages are enabled before moving to the next mode.
        if self.setting_enable_printer_messages:

            self.printer_message_mode = self.get_next_printer_message_mode()

            self.refresh_messages()

    # Refreshes the messages being shown to the user.
    def refresh_messages(self):

        self.logger.debug("refresh_messages called.")

        self.calculate_messages()

        self.logger.debug("ETA string: " + self.eta_string)
        self.logger.debug("Printer message: " + self.printer_message)

        # Compare the new and previous ETA string before pushing any updates to the UI.
        if self.eta_string != self.previous_eta_string:

            self.previous_eta_string = self.eta_string

            self.dispatch_eta_message()

        # Send M117 command to printer, if setting is enabled.
        # Only send M117 if the printer is actually printing. We may reach this part before the printer has
        # actually started printing (for example, when it is probing the bed for auto bed levelling) and some
        # printers show messages on the screen depending on the print's start gcode. We don't want to interfere
        # with this, so only send M117s if the print is actually in progress.
        if self._printer.is_printing() and self.setting_enable_printer_messages:

            if not str.isspace(self.printer_message) and self.printer_message != self.previous_printer_message:

                self.previous_printer_message = self.printer_message

                self.dispatch_printer_message()
                

    # Dispatches the currnent ETA message to the UI.
    def dispatch_eta_message(self):

        self.logger.debug("dispatch_eta_message called.")

        # Notify listeners of new ETA string value.
        self._plugin_manager.send_plugin_message(self._identifier, dict(eta_string = self.eta_string))

    # Dispatches the current printer message to the printer.
    def dispatch_printer_message(self):

        self.logger.debug("dispatch_printer_message called.")

        message = self.printer_message

        # Remove colons, if enabled. 
        if self.setting_remove_colons:
            message = message.replace(":", " ")

        self._printer.commands("M117 {}".format(message))

        self.logger.debug("Sent M117")

__plugin_name__ = "Print ETA"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = PrintETAPlugin()

__plugin_hooks__ = {
    "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
}
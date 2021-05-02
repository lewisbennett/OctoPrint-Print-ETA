# OctoPrint-Print-ETA

An OctoPrint plugin that shows you the time that a print job is estimated to finish.

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/you/OctoPrint-Helloworld/archive/master.zip

## Configuration

### Format time in 24 hour view (13:00) instead of 12 hour view (1:00 PM).

Enable/disable 24 hour time view. This setting affects the way that time is displayed both within OctoPrint, and on your printer (if enabled). This setting is enabled by default.

### Enable fancy text

Enable/disable "fancy" text. For example: "ETA: 18:00 tomorrow" (enabled), "ETA: 18:00 Sun 2" (disabled). This setting is enabled by default.

### Show the ETA on the printer's screen

If enabled, the plugin will send the ETA displayed within OctoPrint to your printer via an `M117` gcode command. This setting is enabled by default.

### Remove colons from the ETA

If enabled, colons (`:`) will be removed from the ETA that is sent to your printer. This is required for some printer firmwares and is disabled by default. The ETA shown within OctoPrint is not affected.

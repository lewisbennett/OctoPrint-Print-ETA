# OctoPrint-Print-ETA

An OctoPrint plugin that shows you the time that a print job is estimated to finish.

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

```
https://github.com/lewisbennett/OctoPrint-Print-ETA/archive/master.zip
```

## Configuration

### Format time in 24 hour view (13:00) instead of 12 hour view (1:00 PM).

Enable/disable 24 hour time view. This setting affects the way that time is displayed both within OctoPrint, and on your printer (if enabled). This setting is enabled by default.

### Show the ETA on the printer's screen

If enabled, the plugin will send the ETA displayed within OctoPrint to your printer via an `M117` gcode command. This setting is enabled by default.

### Remove colons from the ETA

If enabled, colons (`:`) will be removed from the messages that are sent to your printer. This is required for some printer firmwares and is disabled by default. The ETA shown within OctoPrint is not affected.

### Message cycling

If enabled, the plugin will cycle sending different messages to your printer. This setting requires ['Show the ETA on the printer's screen'](#Show-the-ETA-on-the-printer's-screen) to be enabled. This setting is enabled by default, and the messages that are included within the cycle, as well as the cycle interval, can be controlled using the individual settings below.

### Messsage cycling - Include ETA message

This setting controls whether the ETA message (for example: ETA: 13:37 tomorrow) is included within the message cycle, and displayed on your printer's screen. This setting is enabled by default.

### Message cycling - Include time elapsed message

This setting controls whether the time elapsed message (for example: Elapsed: 13h, 37m) is included within the message cycle, and displayed on your printer's screen. This setting is enabled by default.

### Message cycling - Include time remaining message

This setting controls whether the time remaining message (for example: Remaining: 13h, 37m) is included within the message cycle, and dislpayed on your printer's screen. This setting is enabled by default.

### Message cycling - Include progress percentage message

This setting controls whether the progress percentage message (for example: 10% complete) is included within the message cycle, and displayed on your printer's screen. This setting is enabled by default.

### Message cycle interval

This setting controls the interval between messages within the message cycle, in minutes. The default value for this setting is 1 minute.

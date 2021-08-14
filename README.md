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

### Show print progress on the printer's screen (uses M73).

If enabled, the plugin will send print progress percentage updates to the printer's screen via an `M73` gcode command. This will update the progress bar on the screen. This setting is enabled by default.

### Remove colons from the ETA

If enabled, colons (`:`) will be removed from the messages that are sent to your printer. This is required for some printer firmwares and is disabled by default. The ETA shown within OctoPrint is not affected.

### Printer messages (uses M117)

If enabled, the plugin will send information regarding the current print to the printer's screen. These messages can be configured individually or turned off completely. Messages are sent to the printer's screen via an `M117` gcode command. This setting is enabled by default.

### Printer messages - Show ETA message

This setting controls whether the ETA of the active print is displayed on the printer's screen. This setting is enabled by default.

### Printer messages - Show time elapsed

This setting controls whether the time elapsed on the active print is displayed on the printer's screen. This setting is enabled by default.

### Printer messages - Show time remaining

This setting controls whether the time remaining on the active print is displayed on the printer's screen. This setting is enabled by default.

### Printer messages - Show print progress

This setting controls whether the active print's progress is displayed on the printer's screen. This setting is separate from the `M73` based setting above and is disabled by default.

### Printer message interval

This setting controls the interval between new printer messages being displayed, in minutes. The default value is `1`.

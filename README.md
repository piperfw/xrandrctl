# xrandrctl
python 3 wrapper for `xrandr` to control screen brightness and colour

This script stores the current values of the `brightness` and `gamma` properties for outputs recognised by the `xrandr` program in a JSON document. The script then makes an appropriate call to `xrandr` to change the brightness and/or gamma values of an output by a certain delta. This can be used as a simple tool to control the 'temperature' of your screens. 

Example use:
```
python xrandrctl.py HDMI-1 --brighter --bluer
```

The available options are
`--brighter`
`--dimmer`
`--redder`
`--bluer`, and 
`--reset`,
with obvious meanings.

For those without multiple monitors or the need to control the brightness/gamma of multiple monitors individually, you may want to use the 'mini' version of this wrapper: [`minixrandrctl`.](#minixrandrctl)

### Set up
Copy `xrandr_current_values.json` into the directory containing `xrandrctl.py`. This JSON document contains an array of objects (comma separated), each describing one output connected recognised as 'connected' by `xrandr` (and supporting changes in gamma and brightness).
The only fields absolutely required in each dictionary are the `output`, `brightness` and `gamma` fields. `output` is the name of the connected display as listed by running `xrandr`. For example, `"output": "DVI-I-1"`. `brightness` is the saved brightness of the display, which should be `1` before you first run the script. Similarly, `gamma` is the remembered value of the R:G:B gamma triplet for the display as an array of floats and has a starting value of `[1,1,1]`.

Optional fields for an output:
- `alias` - a string that may be used to refer to that output
- `brightness_delta` - a float describing the amount to increment or decrement the value of brightness by (default `0.1`)
- `gamma_delta` - a list of floats describing the amount to increment or decrement the value of gamma by (default `[0,0.025,0.05]`)

An example entry utilising all three optional fields would be
```json
  {
    "alias": "secondary",
    "output": "HDMI-1",
    "brightness": 1.0,
    "gamma": [
      1.0,
      1.0,
      1.0
    ],
    "brightness_delta": 0.15,
    "gamma_delta": [
      0,
      0.03,
      0.06
    ]
  }
```
(I recommend using a plugin or on-line tool to 'prettify' the JSON and check for valid syntax.)

### Control
To increase the brightness and blue values of the output `DVI-D-1`
```
python xrandrctl.py DVI-D-1 --brighter --bluer
```
or, if it has the `alias` 'primary',
```
python xrandrctl.py primary --brighter --bluer
```
To do the above while also decreasing the brightness and blue values of an output with the alias 'secondary'
```
python xrandrctl.py primary --brighter --bluer secondary --dimmer --redder
```

In each case, the commands increment or decrement the brightness and gamma values according to the deltas for that output in `xrandr_current_values.json`, if specified (otherwise the default values defined in `xrandrctl.py` are used).

A bash alias is handy here. For example,
```sh
~/.bashrc
---------
alias xrandctl="python ./my_scripts/xrandrctl.py"
```

To change the brightness or gamma of _all_ outputs added to `xrandr_current_values.json`, simply omit naming the output or its alias. For example,
```
python xrandrctl.py --dimmer
```

Finally, the `--reset` option restores the brightness and gamma of an output to their original values (`1.0` and `1:1:1`), with
```
python xrandrctl.py --reset
```
restoring the brightness and gamma of every output.


# minixrandrctl
Todo

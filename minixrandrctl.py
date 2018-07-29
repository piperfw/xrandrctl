"""
A simplified version of xrandr_controller.py, this increments/decrements the brightness or gamma values of all
screen's listed in MINI_FILE_NAME by the same amount (see XRandrController class variables) based on user input.

For usage please see Readme.md.
"""
import json, sys, operator, subprocess, logging, os, time

# Logging set-up - single file handler to minixrandrctl.log
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Comment out the below lines if you want to disable logging to file.
file_handler = logging.FileHandler(os.path.splitext(__file__)[0] + '.log')
# Edit level here is wish to filter messages to e.g. WARNING only.
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

class XRandrController:
	"""
	CLASS VARIABLES
	---------------
	BRIGHTNESS_DELTA : float
		The value to increment (--brighter) or decrement (--dimmer) all screens' brightness value. 
	GAMMA_DELTA : list of floats
		The values to increment (--bluer) or decrement (--redder) all screens' gamma tripley by.
	MINI_FILE_NAME : string
		The name of the file (JSON document) storing the current values for the brightness/gamma of all screens or
		'outputs'. This must be placed in the same directory as this script.
	ALLOWED_OPTIONS : dictionary
		Each key is an option which may be passed as a command line argument to this program when prefixed with two 
		hyphens, and its value is the default value for that option (all False i.e. 'off').
	RESET_BRIGHTNESS_VALUE : float
		The value to which the brightness of all outputs is set to by the --reset option.
	RESET_GAMMA_VALUE : list of floats
		The values to which the gamma of all outputs is set to by the --reset option.
	"""
	BRIGHTNESS_DELTA = 0.1
	GAMMA_DELTA = [0,0.025,0.05]
	MINI_FILE_NAME = 'minixrandr_current_values.json'
	ALLOWED_OPTIONS = {'redder':False,'bluer':False,'brighter':False,'dimmer':False, 'reset':False}
	RESET_BRIGHTNESS_VALUE = 1
	RESET_GAMMA_VALUE = [1,1,1]

	def __init__(self, arguments):
		# To store MINI_FILE_NAME elsewhere, edit this path construction.
		self.value_file = os.path.join(os.path.dirname(__file__), self.MINI_FILE_NAME)
		logger.debug('Path to current value file: {}'.format(self.value_file))
		# Option flags set according to command line arguments.
		self.arguments = arguments
		# Dictionary to store current values of brightness/gamma for all outputs.
		self.current_values = {}
		# Load self.current_values from self.current_value.
		self.get_current_values()
		# Adjust values in self.current_values based on self.arguments.
		self.set_new_values()
		# Run a xrandr process to change the screens' brightness/gamma according to the adjusted values.
		self.run_xrandr()
		# Write to self.value_file, saving the new values for all outputs.
		self.save_new_values()

	def get_current_values(self):
		"""Load the contents of self.value_file, a JSON doc., into self.current_values (JSON object -> dictionary)."""
		with open(self.value_file, 'r') as f:
			self.current_values = json.load(f)

	def set_new_values(self):
		"""Modify the brightness and gamma fields in self.current_values according to user input (self.arguments) 
		and class variables BRIGHTNESS_DELTA and GAMMA_DELTA.

		If --reset was passed as an argument, the brightness and gamma values are firstly reset to 1 and 1:1:1,
		respectively (self.RESET_BRIGHTNESS_VALUE and self.RESET_GAMMA_VALUE).
		"""
		if self.arguments['reset']:
			self.current_values['gamma'] = self.RESET_GAMMA_VALUE
			self.current_values['brightness'] = self.RESET_BRIGHTNESS_VALUE
		# If option 'bluer' is True, we add gamma_delta to current gamma values. If 'redder' is true we subtract
		gamma_to_add = [x*(int(self.arguments['bluer'])-int(self.arguments['redder'])) for x in self.GAMMA_DELTA]
		self.current_values['gamma'] = list(map(operator.add, self.current_values['gamma'], gamma_to_add))
		# 'brighter' True increases brightness by bright_delta, 'dimmer' True decreases it by the same amount.
		brightness_to_add = self.BRIGHTNESS_DELTA*(int(self.arguments['brighter'])-int(self.arguments['dimmer']))
		self.current_values['brightness'] += brightness_to_add

	def run_xrandr(self):
		"""Run a xrandr process to adjust the gamma/brightness of each output listed in the 'outputs' field of
		self.current_values according to the (modified) values of brightness and gamma in this dictionary.

		See man xrandr for command line usage of xrandr.
		"""
		# List to hold arguments passed to xrandr program.
		xrandr_args = ['xrandr']
		# xrandr takes gamma values as a triplet of strings: R:G:B (each of R,G,B is the string of a float).
		gamma_str = ':'.join([str(x) for x in self.current_values['gamma']])
		# brightness argument must be passed as a string (representing a float).
		brightness_str = str(self.current_values['brightness'])
		# Add arguments for each output (see man xrandr).
		for output in self.current_values['outputs']:
			xrandr_args.extend(['--output', output, '--gamma', gamma_str, '--brightness', brightness_str])
		try:
			logger.debug('Attempting to begin a process with the following arguments: {}'.format(xrandr_args))
			start = time.time() # Debugging - to time the xrandr process.
			# Run the process and capture any output.
			process = subprocess.run(xrandr_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
				universal_newlines=True, timeout=1)
			completed_message = 'xrandr process completed in {:.2f} seconds'.format(time.time()-start)
			if process.stdout:
				completed_message += ' with the following output: {}.'.format((process.stdout))
			else:
				completed_message += '.'
			# Output is sent to xrandr_controller.log.
			logger.info(completed_message)
		except subprocess.TimeoutExpired:
				# Process was killed due to timeout expiring. Log any error and exit.
				error_message = 'Xrandr process failed to complete after 1 second.'.format(1)
				if process.stderr:
					error_message += ' There were the following errors: {}'.format(process.stderr)
				# Log the error and quit. In particular, do no let self.save_new_values be called as it is likely
				# that the outputs' brightness/gamma were not adjusted.
				logger.error(error_message)
				sys.exit(1)

	def save_new_values(self):
		"""Serialise the (modified) self.current_values to self.value_file (a JSON document), to record the values
		of brightness/gamma for all outputs so that these values may be used next time this script is run."""
		logger.info('Current values: {}'.format(self.current_values))
		with open(self.value_file, 'w') as f:
			json.dump(self.current_values, f)

def main():
	# Remove sys.argv[0], which is always just the name of this script.
	del sys.argv[0]
	# Dictionary to hold boolean (True/False) for each option.
	arguments = dict(XRandrController.ALLOWED_OPTIONS)
	# Until no arguments remain.
	while sys.argv:
		option = sys.argv.pop(0)
		# Options must start with '-' (usually '--').
		if not option.startswith('-'):
			logger.error('Options must start with \'--\'. Exiting.')
			sys.exit(1)
		option_stripped = option.strip('-')
		# Check the option name is valid.
		if option_stripped not in XRandrController.ALLOWED_OPTIONS:
			logger.error('{} is an invalid option. Exiting'.format(option_stripped))
			sys.exit(1)
		# Option is known, so set its flag to be True.
		arguments[option_stripped] = True
	# Create anonymous XRandrController object using user arguments. All functionality is initiated in __init__().
	XRandrController(arguments)

if __name__ == '__main__':
	main()
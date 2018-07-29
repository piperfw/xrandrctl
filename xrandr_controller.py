"""
Calls xrandr to change brightness and colour of chosen screens based on user input (brighter, dimmer, redder or 
bluer) and the current values of brightness and colour of those screens, which is recorded in VALUE_FILE_NAME.

For usage please see Readme.md (TODO).
"""

import json, sys, operator, subprocess, logging, os, time

# Logging set-up - single file handler to xrandr_controller.log
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(os.path.splitext(__file__)[0] + '.log')
# Edit level here is wish to filter messages to e.g. WARNING only.
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class XRandrController:
	"""
	CLASS VARIABLES
	---------------
	DEFAULT_BRIGHTNESS_DELTA : float
		The default step to increment (--brighter) or decrement (--dimmer) a screen's brightness value. Used if
		a given screen does not have a brightness_delta field specified in VALUE_FILE_NAME.
	DEFAULT_GAMMA_DELTA : list of floats
		The default step to increment (--bluer) or decrement (--redder) a screen's gamma values, a triplet a floats
		[R:G:B] (in xrandr: R:G:B). Used if a given screen does not have a gamma_delta field specified in 
		VALUE_FILE_NAME.
	VALUE_FILE_NAME : string
		The name of the file (JSON document) storing the current values & increments for the brightness/gamma of a 
		series of screens or 'outputs', as well as any aliases for these outputs. This must be placed in the same 
		directory as this script (to place elsewhere edit this name and the construction of the file's path in 
		__init__).
	ALLOWED_OPTIONS : dictionary
		Each key is an option which may be passed as a command line argument to this program when prefixed with two 
		hyphens, and its value is the default value for that option (all False i.e. 'off').
	"""
	DEFAULT_BRIGHTNESS_DELTA = 0.1
	DEFAULT_GAMMA_DELTA = [0,0.025,0.05]
	VALUE_FILE_NAME = 'xrandr_current_values.json'
	ALLOWED_OPTIONS = {'redder':False,'bluer':False,'brighter':False,'dimmer':False}

	def __init__(self, arguments):
		# To store VALUE_FILE_NAME elsewhere, edit this path construction.
		self.value_file = os.path.join(os.path.dirname(__file__), self.VALUE_FILE_NAME)
		logger.debug('Path to current value file: {}'.format(self.value_file))
		# Option flags set according to command line arguments.
		self.arguments = arguments
		# Stores current values of brightness/gamma for each output. This is a list of dictionaries, each describing
		# one output.
		self.current_values = []
		# Load self.current_values from self.value_file (JSON document).
		self.get_current_values()
		# Adjust values of each output (dictionary) in self.current_values based on self.arguments.
		self.set_new_values()
		# Run a xrandr process to change the screens' brightness/gamma according to the adjusted values.
		self.run_xrandr()
		# Write to self.value_file, saving the new values for each output.
		self.save_new_values()

	def get_current_values(self):
		"""Load the contents of self.value_file, a JSON doc., into self.current_values (JSON array -> list)."""
		with open(self.value_file, 'r') as f:
			self.current_values = json.load(f)

	def set_new_values(self):
		"""Modify each dictionary in self.current_values according to user input (self.arguments) and deltas for
		brightness/gamma stored in the dictionary (otherwise use default deltas). Note that, as mutable objects,
		the dictionaries of self.current_values (as well as the list self.current_values itself), are changed in 
		place.
		"""
		# Iterate through each known output in self.current_values
		for known_output_dict in self.current_values:
			# If the output has an alias, get it.
			alias = known_output_dict.get('alias', None)
			output_name = known_output_dict['output']
			# We need to modify the values for output_name if its alias or name was given as a command line argument,
			# or 'all' was ('all' is set if NO particular output was specified, only options - see main()).
			if alias in self.arguments:
				options = self.arguments[alias]
			elif output_name in self.arguments:
				options = self.arguments[output_name]
			elif 'all' in self.arguments:
				options = self.arguments['all']
			else:
				continue
			# If a 'gamma_delta' property is specified in known_output_dict, use that. Otherwise use the default deltas.
			gamma_delta = known_output_dict.get('gamma_delta', self.DEFAULT_GAMMA_DELTA)
			# If option 'bluer' is True, we add gamma_delta to current gamma values. If 'redder' is true we subtract
			gamma_to_add = [x*(int(options['bluer'])-int(options['redder'])) for x in gamma_delta]
			# map() to add each value of gamma_to_add to the corresponding element in known_output_dict['gamma']
			# (both are lists of three floats) - another list comprehension could be used instead here.
			known_output_dict['gamma'] =  list(map(operator.add, known_output_dict['gamma'], gamma_to_add))
			# Similarly, use the 'brightness_delta' value, if the key exists.
			brightness_delta = known_output_dict.get('brightness_delta', self.DEFAULT_BRIGHTNESS_DELTA)
			# 'brighter' True increases the brightness by bright_delta, while 'dimmer' True decreases it by the same
			# amount (if both specified these options nullify each other, as the 'redder' and 'bluer' do).
			brightness_to_add = brightness_delta*(int(options['brighter'])-int(options['dimmer']))
			known_output_dict['brightness'] += brightness_to_add

	def run_xrandr(self):
		"""Run a xrandr process to adjust the gamma/brightness of each output according to the values in the dictionary
		in self.current_values describing that output. 

		See man xrandr for command line usage of xrandr.
		"""
		# List to hold arguments passed to xrandr program.
		xrandr_args = ['xrandr']
		for known_output_dict in self.current_values:
			# xrandr takes gamma values as a triplet of strings: R:G:B (each of R,G,B is the string of a float).
			gamma_str = ':'.join([str(x) for x in known_output_dict['gamma']])
			# See man xrandr. Note that known_output_dict['output'] must be the name known by xrandr.
			xrandr_args.extend(['--output', known_output_dict['output'], '--gamma', gamma_str, '--brightness', 
				str(known_output_dict['brightness'])])
		try:
			start = time.time() # Debugging - to time the xrandr process.
			logger.debug('Attempting to begin a process with the following arguments: {}'.format(xrandr_args))
			# Run the process and capture any output.
			process = subprocess.run(xrandr_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
				universal_newlines=True, timeout=1)
			completed_message = 'Process completed in {} seconds'.format(time.time()-start)
			if process.stdout:
				completed_message += ' with the following output: {}.'.format((process.stdout))
			else:
				completed_message += '.'
			# Output is sent to xrandr_controller.log.
			logger.debug(completed_message)
		except subprocess.TimeoutExpired:
				# Process was killed due to timeout expiring. Log any error and exit.
				error_message = 'Xrandr process failed to complete after 1 second.'
				if process.stderr:
					error_message += ' There were the following errors: {}'.format(process.stderr)
				# Log the error and quit. In particular, do no let self.save_new_values be called as it is likely
				# that the outputs' brightness/gamma were not adjusted.
				logger.error(error_message)
				sys.exit(1)

	def save_new_values(self):
		"""Serialise the (modified) self.current_values to self.value_file (a JSON document), to record the values
		of brightness/gamma for each output so that these values may be used next time this script is run."""
		logger.info('Current values: {}'.format(self.current_values))
		with open(self.value_file, 'w') as f:
			json.dump(self.current_values, f)

def main():
	# Remove sys.argv[0], which is always just the name of this script.
	del sys.argv[0]
	# Dictionary to store dictionaries holding the options for each output specified by the user.
	arguments = {}
	# Until no arguments remain.
	while sys.argv:
		# 'all' refers to all outputs, and is used if no output is specified in particular, only options.
		output = 'all'
		# Outputs are recognised by NOT starting with '-'.
		if not sys.argv[0].startswith('-'):
			output = sys.argv.pop(0) # E.g. 'primary', 'HDMI-1'
		# Copy XRandrController.ALLOWED_OPTIONS and modify the value of any option passed to the command line
		# for this output.
		arguments[output] = dict(XRandrController.ALLOWED_OPTIONS)
		while True:
			try:
				# IndexError is thrown if this doesn't exist.
				option = sys.argv[0]
				if not option.startswith('-'):
					# We have reached the next output (no starting '-'), so break from the while True loop.
					break
				# Strip the option of its '-' (usually '--').
				option_stripped = option.strip('-')
				# Check the option name is valid. If not, quite (could discard option and look for other valid options).
				if option_stripped not in arguments[output]:
					logger.error('{} is an invalid option. Exiting.'.format(option_stripped))
					sys.exit(1)
				# Option is known, so toggle its flag on (each value in XRandrController.ALLOWED_OPTIONS is a boolean).
				arguments[output][option_stripped] = True
				# Now delete the arguement. The loop continues until the next output is reached 
				# (if not option.startswith('-')) or we hit the end of the argument list (IndexError).
				del sys.argv[0]
			except IndexError:
				break
	# Create anonymous XRandrController object using user arguments. All functionality is initiated in __init__().
	XRandrController(arguments)

if __name__ == '__main__':
	main()
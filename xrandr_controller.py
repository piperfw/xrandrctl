import json, sys, operator, subprocess, logging, os, time

# Logging set-up - single file handler to xrandr_controller.log
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(os.path.splitext(__file__)[0] + '.log')
# Edit level here is wish to filter messages
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class XRandrController:
	DEFAULT_BRIGHTNESS_DELTA = 0.1
	DEFAULT_GAMMA_DELTA = [0,0.025,0.05]
	VALUE_FILE_NAME = 'xrandr_current_values.json'
	ALLOWED_OPTIONS = {'redder':False,'bluer':False,'brighter':False,'dimmer':False}


	def __init__(self, arguments):
		self.value_file = os.path.join(os.path.dirname(__file__), self.VALUE_FILE_NAME)
		logger.debug('Path to current value file: {}'.format(self.value_file))
		self.arguments = arguments
		self.current_values = {}
		self.get_current_values()
		self.set_new_values()
		self.run_xrandr()
		self.save_new_values()

	def get_current_values(self):
		with open(self.value_file, 'r') as f:
			self.current_values = json.load(f)

	def set_new_values(self):
		for known_output_dict in self.current_values:
			alias = known_output_dict['alias']
			if alias in self.arguments:
				options = self.arguments[alias]
			elif 'all' in self.arguments:
				options = self.arguments['all']
			else:
				continue
			gamma_delta = known_output_dict.get('gamma_delta', self.DEFAULT_GAMMA_DELTA)
			gamma_to_add = [x*(int(options['bluer'])-int(options['redder'])) for x in gamma_delta]
			brightness_delta = known_output_dict.get('brightness_delta', self.DEFAULT_BRIGHTNESS_DELTA)
			brightness_to_add = brightness_delta*(int(options['brighter'])-int(options['dimmer']))

			known_output_dict['gamma'] =  list(map(operator.add, known_output_dict['gamma'], gamma_to_add))
			known_output_dict['brightness'] += brightness_to_add

	def run_xrandr(self):
		xrandr_args = ['xrandr']
		for known_output_dict in self.current_values:
			gamma_str = ':'.join([str(x) for x in known_output_dict['gamma']])
			xrandr_args.extend(['--output', known_output_dict['output'], '--gamma', gamma_str, '--brightness', 
				str(known_output_dict['brightness'])])
		try:
			start = time.time()
			logger.debug('Attempting to begin a process with the following arguments: {}'.format(xrandr_args))
			process = subprocess.run(xrandr_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
				universal_newlines=True, timeout=1)
			logger.debug('Process completed in {} seconds'.format(time.time()-start))
		except subprocess.TimeoutExpired:
				# Process was killed due to timeout expiring. Log any error and exit (don't save save values).
				error_message = 'Xrandr process failed to complete after 1 second.'.format(1)
				if process.stderr:
					error_message += ' There were the following errors: {}'.format(process.stderr)
				logger.error(error_message)
				sys.exit(1)

	def save_new_values(self):
		logger.info('Current values: {}'.format(self.current_values))
		with open(self.value_file, 'w') as f:
			json.dump(self.current_values, f)

def main():
	del sys.argv[0]
	arguments = {}
	while sys.argv:
		output = 'all'
		if not sys.argv[0].startswith('-'):
			output = sys.argv.pop(0)
		arguments[output] = dict(XRandrController.ALLOWED_OPTIONS)
		while True:
			try:
				option = sys.argv[0]
				if not option.startswith('-'):
					break
				option_stripped = option.strip('-')
				if option_stripped not in arguments[output]:
					logger.error('{} is an invalid option.'.format(option_stripped))
					sys.exit(1)
				arguments[output][option_stripped] = True
				del sys.argv[0]
			except IndexError:
				break
	XRandrController(arguments)
	# print(arguments)


if __name__ == '__main__':
	main()
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
	ALLOWED_OPTIONS = {'redder':False,'bluer':False,'brighter':False,'dimmer':False}
	BRIGHTNESS_DELTA = 0.1
	GAMMA_DELTA = [0,0.025,0.05]
	MINI_FILE_NAME = 'xrandr_current_values_simple.json'

	def __init__(self, arguments):
		self.value_file = os.path.join(os.path.dirname(__file__), self.MINI_FILE_NAME)
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
		gamma_to_add = [x*(int(self.arguments['bluer'])-int(self.arguments['redder'])) for x in self.GAMMA_DELTA]
		brightness_to_add = self.BRIGHTNESS_DELTA*(int(self.arguments['brighter'])-int(self.arguments['dimmer']))
		self.current_values['gamma'] = list(map(operator.add, self.current_values['gamma'], gamma_to_add))
		self.current_values['brightness'] += brightness_to_add

	def run_xrandr(self):
		xrandr_args = ['xrandr']
		gamma_str = ':'.join([str(x) for x in self.current_values['gamma']])
		brightness_str = str(self.current_values['brightness'])
		for output in self.current_values['outputs']:
			xrandr_args.extend(['--output', output, '--gamma', gamma_str, '--brightness', brightness_str])
		try:
			logger.debug('Attempting to begin a process with the following arguments: {}'.format(xrandr_args))
			start = time.time()
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
	arguments = dict(XRandrController.ALLOWED_OPTIONS)
	while sys.argv:
		option = sys.argv.pop(0)
		if not option.startswith('-'):
			logger.error('Options begin start with \'--\'.')
			sys.exit(1)
		option_stripped = option.strip('-')
		if option_stripped not in XRandrController.ALLOWED_OPTIONS:
			logger.error('{} is an invalid option.'.format(option_stripped))
			sys.exit(1)
		arguments[option_stripped] = True
	XRandrController(arguments)

if __name__ == '__main__':
	main()
from modules.gui import GUIController
print('GUIController class:', GUIController)
inst = GUIController()
print('instance type:', type(inst))
print('has run attribute?', hasattr(inst, 'run'))
print('run attr:', getattr(inst, 'run', None))
print('dir includes run?', 'run' in dir(inst))

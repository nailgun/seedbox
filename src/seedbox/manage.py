from flask_script import Manager
from flask_migrate import MigrateCommand

from seedbox.app import app


def run():
    manager = Manager(app)
    manager.add_command('db', MigrateCommand)
    manager.run()


if __name__ == '__main__':
    run()

import logging

from flask_script import Manager
from flask_migrate import MigrateCommand

from seedbox.app import app

manager = Manager(app)
manager.add_command('db', MigrateCommand)


@manager.command
def watch_updates():
    """Starts component updates watcher in foreground (CoreOS, k8s, etcd)"""
    from seedbox import update_watcher
    update_watcher.watch()


def run():
    logging.basicConfig(level='NOTSET')
    manager.run()


if __name__ == '__main__':
    run()

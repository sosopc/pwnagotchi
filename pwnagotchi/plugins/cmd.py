# Handles the commandline stuff

import os
import logging
import glob
import shutil
from fnmatch import fnmatch
from pwnagotchi.utils import download_file, unzip, save_config, parse_version,\
    md5, pip_install, analyze_plugin, has_internet
from pwnagotchi.plugins import default_path


SAVE_DIR = '/usr/local/share/pwnagotchi/availaible-plugins/'
DEFAULT_INSTALL_PATH = '/usr/local/share/pwnagotchi/installed-plugins/'


def add_parsers(parser):
    """
    Adds the plugins subcommand to a given argparse.ArgumentParser
    """
    subparsers = parser.add_subparsers()
    ## pwnagotchi plugins
    parser_plugins = subparsers.add_parser('plugins')
    plugin_subparsers = parser_plugins.add_subparsers(dest='plugincmd')

    ## pwnagotchi plugins search
    parser_plugins_search = plugin_subparsers.add_parser('search', help='Search for pwnagotchi plugins')
    parser_plugins_search.add_argument('pattern', type=str, help="Search expression (wildcards allowed)")

    ## pwnagotchi plugins list
    parser_plugins_list = plugin_subparsers.add_parser('list', help='List available pwnagotchi plugins')

    ## pwnagotchi plugins update
    parser_plugins_update = plugin_subparsers.add_parser('update', help='Updates the database')

    ## pwnagotchi plugins upgrade
    parser_plugins_upgrade = plugin_subparsers.add_parser('upgrade', help='Upgrades plugins')
    parser_plugins_upgrade.add_argument('pattern', type=str, nargs='?', default='*', help="Filter expression (wildcards allowed)")

    ## pwnagotchi plugins enable
    parser_plugins_enable = plugin_subparsers.add_parser('enable', help='Enables a plugin')
    parser_plugins_enable.add_argument('name', type=str, help='Name of the plugin')

    ## pwnagotchi plugins disable
    parser_plugins_disable = plugin_subparsers.add_parser('disable', help='Disables a plugin')
    parser_plugins_disable.add_argument('name', type=str, help='Name of the plugin')

    ## pwnagotchi plugins install
    parser_plugins_install = plugin_subparsers.add_parser('install', help='Installs a plugin')
    parser_plugins_install.add_argument('name', type=str, help='Name of the plugin')

    ## pwnagotchi plugins uninstall
    parser_plugins_uninstall = plugin_subparsers.add_parser('uninstall', help='Uninstalls a plugin')
    parser_plugins_uninstall.add_argument('name', type=str, help='Name of the plugin')

    ## pwnagotchi plugins edit
    parser_plugins_edit = plugin_subparsers.add_parser('edit', help='Edit the options')
    parser_plugins_edit.add_argument('name', type=str, help='Name of the plugin')

    return parser


def used_plugin_cmd(args):
    """
    Checks if the plugins subcommand was used
    """
    return hasattr(args, 'plugincmd')


def handle_cmd(args, config):
    """
    Parses the arguments and does the thing the user wants
    """
    if args.plugincmd == 'update':
        return update(config)
    elif args.plugincmd == 'search':
        args.installed = True # also search in installed plugins
        return list_plugins(args, config, args.pattern)
    elif args.plugincmd == 'install':
        return install(args, config)
    elif args.plugincmd == 'uninstall':
        return uninstall(args, config)
    elif args.plugincmd == 'list':
        return list_plugins(args, config)
    elif args.plugincmd == 'enable':
        return enable(args, config)
    elif args.plugincmd == 'disable':
        return disable(args, config)
    elif args.plugincmd == 'upgrade':
        return upgrade(args, config, args.pattern)
    elif args.plugincmd == 'edit':
        return edit(args, config)

    raise NotImplementedError()


def edit(args, config):
    """
    Edit the config of the plugin
    """
    plugin = args.name
    editor = os.environ.get('EDITOR', 'vim') # because vim is the best

    if plugin not in config['main']['plugins']:
        return 1

    plugin_config = {'main': {'plugins': {plugin: config['main']['plugins'][plugin]}}}

    import toml
    from subprocess import call
    from tempfile import NamedTemporaryFile
    from pwnagotchi.utils import DottedTomlEncoder

    new_plugin_config = None
    with NamedTemporaryFile(suffix=".tmp", mode='r+t') as tmp:
        tmp.write(toml.dumps(plugin_config, encoder=DottedTomlEncoder()))
        tmp.flush()
        rc = call([editor, tmp.name])
        if rc != 0:
            return rc
        tmp.seek(0)
        new_plugin_config = toml.load(tmp)

    config['main']['plugins'][plugin] = new_plugin_config['main']['plugins'][plugin]
    save_config(config, args.user_config)
    return 0


def enable(args, config):
    """
    Enables the given plugin and saves the config to disk
    """
    if args.name not in config['main']['plugins']:
        config['main']['plugins'][args.name] = dict()
    config['main']['plugins'][args.name]['enabled'] = True
    save_config(config, args.user_config)
    return 0


def disable(args, config):
    """
    Disables the given plugin and saves the config to disk
    """
    if args.name not in config['main']['plugins']:
        config['main']['plugins'][args.name] = dict()
    config['main']['plugins'][args.name]['enabled'] = False
    save_config(config, args.user_config)
    return 0


def upgrade(args, config, pattern='*'):
    """
    Upgrades the given plugin
    """
    available = _get_available()
    installed = _get_installed(config)

    for plugin, filename in installed.items():
        if not fnmatch(plugin, pattern) or plugin not in available:
            continue

        available_plugin_data = analyze_plugin(available[plugin])
        available_version = parse_version(available_plugin_data['__version__'])
        installed_version = parse_version(analyze_plugin(filename)['__version__'])

        if installed_version and available_version:
                if available_version <= installed_version:
                    continue
        else:
            continue

        logging.info('Upgrade %s from %s to %s', plugin, '.'.join(installed_version), '.'.join(available_version))

        if '__dependencies__' in available_plugin_data:
            deps = available_plugin_data['__dependencies__']
            if deps:
                for d in deps:
                    if not pip_install(d):
                        logging.error('Dependency "%s" not found', d)
                        return 1

        if '__assets__' in available_plugin_data:
            assets = available_plugin_data['__assets__']
            if assets:
                if not isinstance(assets, list):
                    assets = [assets]

                for a in assets:
                    if a.startswith('https://'):
                        dst = os.path.join(os.path.dirname(installed[plugin]), os.path.basename(a))
                        if not os.path.exists(dst) and not has_internet():
                            logging.error('Could not download asset %s', a)
                            return 1
                        logging.info('Downloading asset: %s', os.path.basename(a))
                        download_file(a, dst)
                        continue


                    for f in glob.glob(a):
                        dst = os.path.join(os.path.dirname(installed[plugin]), os.path.basename(f))
                        logging.info('Copy asset: %s', os.path.basename(f))
                        shutil.copyfile(f, dst)


        shutil.copyfile(available[plugin], installed[plugin])

        # maybe has config
        for conf in glob.glob(available[plugin].replace('.py', '.[yt][oa]?ml')):
            dst = os.path.join(os.path.dirname(installed[plugin]), os.path.basename(conf))
            if os.path.exists(dst) and md5(dst) != md5(conf):
                # backup
                logging.info('Backing up config: %s', os.path.basename(conf))
                shutil.move(dst, dst + '.bak')
            shutil.copyfile(conf, dst)

    return 0


def list_plugins(args, config, pattern='*'):
    """
    Lists the available and installed plugins
    """
    found = False

    line = "|{name:^{width}}|{version:^9}|{enabled:^10}|{status:^15}|"

    available = _get_available()
    installed = _get_installed(config)

    available_and_installed = set(list(available.keys()) + list(installed.keys()))
    available_not_installed = set(available.keys()) - set(installed.keys())

    max_len = max(map(len, available_and_installed))
    header = line.format(name='Plugin', width=max_len, version='Version', enabled='Active', status='Status')
    line_length = max(max_len, len('Plugin')) + len(header) - len('Plugin') - 12 # lol

    print('-' * line_length)
    print(header)
    print('-' * line_length)

    # only installed (maybe update available?)
    for plugin, filename in sorted(installed.items()):
        if not fnmatch(plugin, pattern):
            continue
        found = True
        plugin_info = analyze_plugin(filename)
        installed_version = parse_version(plugin_info['__version__'])
        available_version = None
        if plugin in available:
            available_plugin_info = analyze_plugin(available[plugin])
            available_version = parse_version(available_plugin_info['__version__'])

        status = "installed"
        if installed_version and available_version:
            if available_version > installed_version:
                status = "installed (^)"

        enabled = 'enabled' if plugin in config['main']['plugins'] and \
            'enabled' in config['main']['plugins'][plugin] and \
                config['main']['plugins'][plugin]['enabled'] \
                    else 'disabled'

        print(line.format(name=plugin, width=max_len, version='.'.join(installed_version), enabled=enabled, status=status))


    for plugin in sorted(available_not_installed):
        if not fnmatch(plugin, pattern):
            continue
        found = True
        available_plugin_info = analyze_plugin(available[plugin])
        available_version = available_plugin_info['__version__']
        print(line.format(name=plugin, width=max_len, version=available_version, enabled='-', status='available'))

    print('-' * line_length)

    if not found:
        logging.info('Maybe try: pwnagotchi plugins update')
        return 1
    return 0


def _get_available():
    """
    Get all availaible plugins
    """
    available = dict()
    for filename in glob.glob(os.path.join(SAVE_DIR, "*.py")):
        plugin_name = os.path.basename(filename.replace(".py", ""))
        available[plugin_name] = filename
    return available


def _get_installed(config):
    """
    Get all installed plugins
    """
    installed = dict()
    search_dirs = [ default_path, config['main']['custom_plugins'] ]
    for search_dir in search_dirs:
        if search_dir:
            for filename in glob.glob(os.path.join(search_dir, "*.py")):
                plugin_name = os.path.basename(filename.replace(".py", ""))
                installed[plugin_name] = filename
    return installed


def uninstall(args, config):
    """
    Uninstalls a plugin
    """
    plugin_name = args.name
    installed = _get_installed(config)
    if plugin_name not in installed:
        logging.error('Plugin %s is not installed.', plugin_name)
        return 1

    plugin_info = analyze_plugin(installed[plugin_name])

    if '__assets__' in plugin_info:
        assets = plugin_info['__assets__']
        if assets:
            if not isinstance(assets, list):
                assets = [assets]

            for a in assets:
                for f in glob.glob(a):
                    logging.info('Delete asset: %s', os.path.basename(f))
                    os.remove(f)

    os.remove(installed[plugin_name])
    # but keep config

    return 0


def install(args, config):
    """
    Installs the given plugin
    """
    global DEFAULT_INSTALL_PATH
    plugin_name = args.name
    available = _get_available()
    installed = _get_installed(config)

    if plugin_name not in available:
        logging.error('%s not found.', plugin_name)
        return 1

    if plugin_name in installed:
        logging.error('%s already installed.', plugin_name)

    # install into custom_plugins path
    install_path = config['main']['custom_plugins']
    if not install_path:
        install_path = DEFAULT_INSTALL_PATH
        config['main']['custom_plugins'] = install_path
        save_config(config, args.user_config)


    plugin_info = analyze_plugin(available[plugin_name])
    if '__dependencies__' in plugin_info:
        deps = plugin_info['__dependencies__']
        if deps:
            for d in deps:
                if not pip_install(d):
                    logging.error('Dependency "%s" not found', d)
                    return 1

    os.makedirs(install_path, exist_ok=True)

    if '__assets__' in plugin_info:
        assets = plugin_info['__assets__']
        if assets:
            if not isinstance(assets, list):
                assets = [assets]

            for a in assets:
                if a.startswith('https://'):
                    dst = os.path.join(install_path, os.path.basename(a))
                    if not os.path.exists(dst) and not has_internet():
                        logging.error('Could not download asset %s', a)
                        return 1
                    logging.info('Downloading asset: %s', os.path.basename(a))
                    download_file(a, dst)
                    continue

                for f in glob.glob(a):
                    dst = os.path.join(install_path, os.path.basename(f))
                    logging.info('Copy asset: %s', os.path.basename(f))
                    shutil.copyfile(f, dst)

    shutil.copyfile(available[plugin_name], os.path.join(install_path, os.path.basename(available[plugin_name])))

    # maybe has config
    for conf in glob.glob(available[plugin_name].replace('.py', '.y?ml')):
        dst = os.path.join(install_path, os.path.basename(conf))
        if os.path.exists(dst) and md5(dst) != md5(conf):
            # backup
            logging.info('Backing up config: %s', os.path.basename(conf))
            shutil.move(dst, dst + '.bak')
        shutil.copyfile(conf, dst)

    return 0


def _analyse_dir(path):
    results = dict()
    path += '*' if path.endswith('/') else '/*'
    for filename in glob.glob(path, recursive=True):
        if not os.path.isfile(filename):
            continue
        try:
            results[filename] = md5(filename)
        except OSError:
            continue
    return results


def update(config):
    """
    Updates the database
    """
    global SAVE_DIR

    urls = config['main']['custom_plugin_repos']
    if not urls:
        logging.info('No plugin repositories configured.')
        return 1

    rc = 0
    for idx, REPO_URL in enumerate(urls):
        DEST = os.path.join(SAVE_DIR, 'plugins%d.zip' % idx)
        logging.info('Downloading plugins from %s to %s', REPO_URL, DEST)

        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            before_update = _analyse_dir(SAVE_DIR)

            download_file(REPO_URL, os.path.join(SAVE_DIR, DEST))

            logging.info('Unzipping...')
            unzip(DEST, SAVE_DIR, strip_dirs=1)

            after_update = _analyse_dir(SAVE_DIR)

            b_len = len(before_update)
            a_len = len(after_update)

            if a_len > b_len:
                logging.info('Found %d new file(s).', a_len - b_len)

            changed = 0
            for filename, filehash in after_update.items():
                if filename in before_update and filehash != before_update[filename]:
                    changed += 1

            if changed:
                logging.info('%d file(s) were changed.', changed)

        except Exception as ex:
            logging.error('Error while updating plugins: %s', ex)
            rc = 1
    return rc

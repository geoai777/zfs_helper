#!/usr/bin/python3 
# -*- coding: utf-8 -*-

# [ PERMISSIONS ]
from os import geteuid
if geteuid():
    print ("Sorry, we need root permissions to run, bye!")
    exit()


import urwid
from subprocess import Popen, PIPE
from json import loads
from re import match
from apt import Cache

class CascadingBoxes(urwid.WidgetPlaceholder):
    """
    Class that allows to create overlay window
    """
    def __init__(self, box):
        """
        Here we initialize class and pass widget that will take place of background.
        """
        super(CascadingBoxes, self).__init__(box)
        self._level = 0

    def open_box(self, box, title_text=''):
        """
        Opens new window with widget passed by argument
        :box: urwid.[widget]
        """       
        w = urwid.LineBox(box, title=title_text)
        w = urwid.Overlay(w, self.original_widget, ('fixed left', 4), ('fixed right', 5), ('fixed top', 3), ('fixed bottom', 4))
        self.original_widget = w
        self._level += 1

    def keypress(self, size, key):
        """
        On esc closes popup window
        """
        if key == 'esc' and self._level > 0: 
            self.original_widget = self.original_widget[0]
            self._level -= 1
        else:
            return super(CascadingBoxes, self).keypress(size, key)



class ZfsRequires (object):
    """
    Class manages installing additional packages

    TODO:
    - yum package handling
    - dnf package handling
    """

    packages_required = ["zfsutils-linux", "debootstrap", "gdisk", "zfs-initramfs"]
  
    def __init__(self):
        if not self.packages_required:
            return False
        self.os = (self.detect_os()).strip()
        if self.os == 'debian':
            self._package_cache = Cache()

    # [ EXECUTOR ]
    def load_runner(self, cmd):
        """
        Executes given command and returns errors if any
        :cmd: [list]
        :ret: [list]
        """
        cmd = ' '.join(cmd)
        cmd_out = Popen(cmd, shell=True, bufsize=1, stdout=PIPE, stderr=PIPE)

        ret = []
        for pipe in cmd_out.communicate():
            ret.append(pipe.decode('utf-8'))
        return ret


    def detect_os(self):
        """
        Detects OS family for correct package installation
        :returns: str
        """
        return self.load_runner(['cat /etc/os-release', '| grep ID_LIKE', '| awk -F \'=\' \'{print $2}\''])[0]

    def apt_update(self):
        """
        Updates apt package cahe
        :msg: Success or False if not needed
        """

        print(" [ Checking that requied packages are present ]")
        msg = []
        for this_package in self.packages_required:

            if not self._package_cache[this_package].is_installed:
                self._package_cache.update()
                msg.append('Package cache updated')
                msg.append(self.apt_install())
                break
            else:
                msg.append('Package '+this_package+' present')

        return msg

    def apt_install(self):
        """
        Installs packages from packages_required
        """
        res = []
        for this_package in self.packages_required:

            if not self._package_cache[this_package].is_installed:
                self._package_cache[this_package].mark_install()
                res.append(' '.join(['Package', this_package, 'marked for install.\n']))

        self._package_cache.commit()
        return ''.join(res)


class ZfsDrive (object):
    pool_options = []
    pool_defaults = [
        { 'type': 'property', 'name': 'altroot',    'default': '',      'mode': ['create', 'import'] },
        { 'type': 'property', 'name': 'readonly',   'default': 'off',   'mode': ['create', 'import', 'set'] },
        { 'type': 'property', 'name': 'autoexpand', 'default': 'off',   'mode': ['create', 'import', 'set'] },
        { 'type': 'property', 'name': 'autoreplace', 'default': 'off',  'mode': ['create', 'import', 'set'] },
        { 'type': 'property', 'name': 'bootfs',     'default': '',      'mode': ['create', 'import'] },
        { 'type': 'property', 'name': 'cachefile',  'default': '',      'mode': ['create', 'import'] },
        { 'type': 'property', 'name': 'comment',    'default': '',      'mode': ['create', 'import', 'set'] },
        { 'type': 'property', 'name': 'dedupditto', 'default': '0',       'mode': ['create'] },
        { 'type': 'property', 'name': 'delegation', 'default': 'off',   'mode': ['create', 'import', 'set'] },
        { 'type': 'property', 'name': 'failmode',   'default': 'wait',   'mode': ['create', 'import', 'set'] }, #[wait, continue, panic]
        { 'type': 'property', 'name': 'listsnapshots', 'default': 'off',   'mode': ['create', 'import', 'set'] },
        { 'type': 'property', 'name': 'multihost',  'default': 'off',   'mode': ['import'] },
        { 'type': 'feature', 'compatible': True,    'default': '12',        'ro': None,    'os': 'linux', 'name': 'ashift' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'linux', 'name': 'feature@async_destroy' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'solar', 'name': 'feature@allocation_classes' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'linux', 'name': 'feature@bookmarks' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': False,   'os': 'linux', 'name': 'feature@embedded_data' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'linux', 'name': 'feature@empty_bpobj' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'linux', 'name': 'feature@enabled_txg' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': False,   'os': 'linux', 'name': 'feature@extensible_dataset' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'linux', 'name': 'feature@filesystem_limits' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': False,   'os': 'linux', 'name': 'feature@hole_birth' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': False,   'os': 'linux', 'name': 'feature@large_blocks' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': False,   'os': 'linux', 'name': 'feature@lz4_compress' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'solar', 'name': 'feature@project_quota' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'solar', 'name': 'feature@resilver_defer' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'linux', 'name': 'feature@spacemap_histogram' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'solar', 'name': 'feature@spacemap_v2' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'linux', 'name': 'feature@userobj_accounting' },
        { 'type': 'feature', 'compatible': True,    'default': 'enabled',   'ro': True,    'os': 'solar', 'name': 'feature@zpool_checkpoint' },
        { 'type': 'feature', 'compatible': False,   'default': 'disabled',  'ro': True,    'os': 'linux', 'name': 'feature@multi_vdev_crash_dump' },
        { 'type': 'feature', 'compatible': False,   'default': 'disabled',  'ro': False,   'os': 'linux', 'name': 'feature@large_dnode' },
        { 'type': 'feature', 'compatible': False,   'default': 'disabled',  'ro': False,   'os': 'linux', 'name': 'feature@sha512' },
        { 'type': 'feature', 'compatible': False,   'default': 'disabled',  'ro': False,   'os': 'linux', 'name': 'feature@skein' },
        { 'type': 'feature', 'compatible': False,   'default': 'disabled',  'ro': False,   'os': 'linux', 'name': 'feature@edonr' },
    ]
    raid_types = [
        { 'name': 'Stripe',     'mindisk': 1, 'cmd': '' },
        { 'name': 'Mirror',     'mindisk': 2, 'cmd': 'mirror' },
        { 'name': 'RAID-Z L1',  'mindisk': 3, 'cmd': 'raidz'  },
        { 'name': 'RAID-Z L2',  'mindisk': 4, 'cmd': 'raidz2' },
        { 'name': 'RAID-Z L3',  'mindisk': 5, 'cmd': 'raidz3' }
    ]
    fs_options = []
    fs_defaults = [
        { 'op1': 'op' }
    ]
    names_denied = ['log', 'mirror', 'raidz', 'raidz2', 'raidz3', 'spare']

    def __init__(self):
        self.zpool = '/sbin/zpool'
    
    def name_validator(self, name, type='fs'):
        """
        Made to verify, that pools/fs are named according to rules
        """
        if not name:
            return "Empty name is not allowed!"

        if not match('^[a-zA-Z0-9_\-.:]+$', name):
            return "Illegal character in name!"

        if type == "pool":
            if not match('^[a-zA-Z]+', name):
                return "Start with letter!"
            for denied in self.names_denied:
                if match('^'+denied+'.*', name):
                    return "Illegal folder name " + name

        if type == "dataset":
            if not match('^[a-zA-Z]+', name):
                return "Start with letter!"

        return "valid"

    # [ DISKS ]
    def list_disks(self):
        """
        Returns all disks available in system
        Major information is found here:
        https://www.kernel.org/doc/Documentation/admin-guide/devices.txt
        :return: list[dict]
        """
        cmd_disks = Popen("/bin/lsblk -I 3,8 -p -o NAME,FSTYPE,SIZE,MOUNTPOINT -J", shell=True, stdout=PIPE)
        
        return loads(cmd_disks.communicate()[0])['blockdevices']

    # [ EXECUTOR ]
    def load_runner(self, cmd):
        """Executes given command and returns errors if any"""
        cmd = ' '.join(cmd)
        cmd_out = Popen(cmd, shell=True, bufsize=1, stdout=PIPE, stderr=PIPE)

        ret = []
        for pipe in cmd_out.communicate():
            ret.append(pipe.decode('utf-8'))
        return ret


    # [ POOLS ]
    def list_pool_defaults(self):
        """
        Returns default pool options
        :return: list[dict]
        """
        return self.pool_defaults
    
    def set_pool_options(self, options):
        """
        Gets option input and stores in class
        :options: list[dict]
        """
        self.pool_options = options

    def create_pool(self, name, disks, raid='Stripe', force="false", options=[]):
        """
        Create zpool, syntax:
        zpool create <name> <raid> disks/partitions
        :name: str
        :disks: [list]
        :raid: str
        :options: [list{dict}]
        """
        if not self.name_validator(name, 'pool') == 'valid':
            return False

        cmd = [self.zpool, 'create']
        if force:
            cmd.append('-f')

        if not options and not self.pool_options:
            options = self.pool_defaults
        for this_option in options:
            if this_option['type'] == 'property' and not this_option['default'] in ['', 'off', 'wait', '0']:
                cmd.append(' '.join([
                        '-O',
                        ''.join([this_option['name'], '=', this_option['default']])
                    ])
                )
            if this_option['type'] == 'feature' and this_option['default'] == 'enabled' and this_option['os'] == 'linux':
                cmd.append(' '.join(['-o', ''.join([this_option['name'], '=', this_option['default']])]))

        cmd.append(name)

        for this_raid in self.raid_types:
            if this_raid['name'] == raid:
                cmd.append(this_raid['cmd'])
                break

        if not disks:
            return False
        cmd.extend(disks)

        return self.load_runner(cmd)

    def edit_pool(self, name, options):
        """
        Designed to change pool options after pool is created
        """
        return True

    def delete_pool(self, name, force=False):
        """
        Destroys given pool
        :name: str
        :force: bool
        """
        if not name:
            return False

        cmd = [self.zpool]
        if force:
            cmd.append('-f')
        cmd.extend(['destroy', name])

        return self.load_runner(cmd)


    def list_zpools(self):
        """displays available zpools"""
        cmd = [self.zpool, 'list', '| sed 1d', '| awk -F \' +\' \'{print "name:"$1",size:"$2",free:"$4",frag:"$6",status:"$9",altroot:"$10}\'']
        ret_list = self.load_runner(cmd)[0].splitlines()
        ret = []
        for line in ret_list:
            ret.append(dict(x.split(":") for x in line.split(",")))
        
        return ret


    def impex_pool(self, name, type='import', force=False):
        """
        Imports/exports pool to/from system, syntax
        zpool import [-f] pool
        """
        cmd = [self.zpool]
        if type == 'import':
            cmd.append(type)
        else:
            cmd.append('export')
        if force:
            cmd.append('-f')
        cmd.append(name)

        return self.load_runner(cmd)[1]

    def export_pool(self, name, force=False):
        """
        Exports pool from system
        """
        return name
    
    # [ FS ]
    def list_fs_defaults(self):
        """
        Returns default fs options
        :return: list[dict]
        """
        return self.fs_defaults

    def set_fs_options(self, options):
        """
        Gets option input and stores in class
        """
        self.fs_options = options


class ZfsGuiModel (object):
    """
    Data model class. Aims to lighten GUI class.
    """
    def __init__(self, caller_self):
        """
        :caller_self: destination class reference
        """
        self.caller_self = caller_self

    def disk_list(self, disk_list_full_attr):
        """
        Prepares list of disks
        :disk_list_full_attr: list[]
        :return: list[widgets]
        """
        ret_list = []

        if disk_list_full_attr:
            for disk in disk_list_full_attr:
                disk_info = 'Size: ' + str(disk['size']) + '\n' \
                    + 'Mounted: ' + str(disk['mountpoint'])

                if 'children' in disk:
                    for this_child in disk['children']:
                        disk_info += '\n ' + '{:5s} {:5s} {:5s} {}'.format(
                            str(this_child['name'])[5:],
                            str(this_child['size']),
                            str(this_child['fstype']),
                            str(this_child['mountpoint'])
                        )
                        del this_child

                ret_list.append(
                    urwid.LineBox(
                        urwid.Text(disk_info), title=str(disk['name'])
                    )
                )
        else:
            ret_list.append(urwid.Text(u'Merry! There are no disks! How did you boot?'))

        return ret_list

    def zfs_pools(self, zpool_list_raw):
        """
        Prepare pools data
        """
        listing_header = urwid.Text(' {:7s} {:5s} {:4s} {}'.format('Total', 'Free', 'Frag', 'Status'))
        zpool_list = [listing_header]

        if zpool_list_raw:

            for this_pool in list(zpool_list_raw):

                zpool_name          = str(this_pool['name'])
                size_n_free_n_frag  = '{:5s} {:5s} {:4s}'.format(this_pool['size'], this_pool['free'], this_pool['frag'],)
                status              = this_pool['status']
                alt_root            = this_pool['altroot']

                button_text         = ' '.join([size_n_free_n_frag, status, '\n', alt_root])

                button_widget = self.caller_self.button(button_text, self.caller_self.btn_edit_zpool, zpool_name, zpool_name)
                
                zpool_list.append(button_widget)
                del zpool_name

            del zpool_list_raw
        else:
            zpool_list.append(urwid.Text(u'No zpools yet'))

        return zpool_list

    def button_menu(self):
        """
        Prepares list of widgets for menu. Mostly it's buttons
        :return: list[widgets]
        """
        self.menu_buttons = [
            {'name':'Create', 'sub':[
                    { 'name':'Zpool...', 'call':self.caller_self.btn_create_zpool },
                    { 'name':'ZFS...', 'call':self.caller_self.btn_create_zfs }
                ]
            },
            {'name':'Import...', 'call':self.caller_self.btn_import },
            {'name':'Exit', 'call':self.caller_self.exit_program }
        ]

        widget_list = []
        for this_item in self.menu_buttons:
            widget_list.append(self.caller_self.hd)

            if 'call' in this_item:
                widget_list.append(self.caller_self.button(this_item['name'], this_item['call']))
            else:
                widget_list.append(urwid.Text(this_item['name']))

            if 'sub' in this_item:
                for this_sub in this_item['sub']:
                    widget_list.append(urwid.Padding(self.caller_self.button(this_sub['name'], this_sub['call']), left=2, right=1  ))
        widget_list.append(self.caller_self.hd)

        return widget_list


class ZfsGui (object):
    hd = urwid.Divider()
    vd = urwid.AttrMap(urwid.SolidFill(u'\u2502'), 'line')
    palette = [
        # handle         color          bg-color        font options
        ('header',       'light gray',   'black',        'bold'),
        ('fheader',      'white',        'black',        'bold'),
        ('body',         'black',        'light gray',   'standout'),
        ('reverse',      'light gray',   'black'),
        ('screen edge',  'light blue',   'dark cyan'),
        ('main shadow',  'dark gray',    'black'),
        ('button normal','white',        'dark gray',    'standout'),
        ('button select','light cyan',   'black'),
        ('line',         'black',        'light gray',   'standout'),
        ('online',       'dark green',   '',             'bold')
    ]

    def __init__(self):
        self.mothership_core = ZfsDrive()
        self.log = []
        self.handle = {}

        # All urwid staff happens in this function
        self._system_update = ZfsRequires()

        if self._system_update.os == 'debian':
            upd_msg = self._system_update.apt_update()

            for this_msg in upd_msg:
                self.log.insert(0, urwid.Text(this_msg))

        self.init_window()
        
        
    
    # [ URWID AND GUI ]
    def grab_input(self, key):
        """
        Grab key, make action
        """
        if key == 'f5':
            self.frame_refresh(self.model.disk_list(self.mothership_core.list_disks()), 'dlist')
            self.frame_refresh(self.model.zfs_pools(self.mothership_core.list_zpools()), 'zlist')

        if key == 'q' or key == 'й' or key == 'ქ':
            raise urwid.ExitMainLoop()

    def log_it(self, log_msg):
        self.panel_update(self.log_box, urwid.Text(log_msg))

    def main_shadow(self, w, type=''):
        """
        Wrap a shadow and background around widget w.
        """
        border_margins = [
            { 'sl':3, 'sr':1, 'st':2, 'sb':1, 'bl':2, 'br':3, 'bt':1, 'bb':2 },
            { 'sl':8, 'sr':6, 'st':7, 'sb':6, 'bl':7, 'br':8, 'bt':6, 'bb':7 }
        ]
        n = 0
        if type:
            n = 1
        
        br = border_margins[n]
        bg = urwid.AttrMap(urwid.SolidFill(u"\u2592"), 'screen edge')
        shadow = urwid.AttrMap(urwid.SolidFill(u" "), 'main shadow')

        bg = urwid.Overlay( shadow, bg,
            ('fixed left', br['sl']), ('fixed right', br['sr']),
            ('fixed top', br['st']), ('fixed bottom', br['sb']))
        w = urwid.Overlay( w, bg,
            ('fixed left', br['bl']), ('fixed right', br['br']),
            ('fixed top', br['bt']), ('fixed bottom', br['bb']))
        return w

    def panel_update(self, dst, obj, position='top'):
        """
        Add desired object to panel
        :dst: object(self.<panel_name>)
        :obj: object(what to append)
        :position: int
        """
        if position != 'top':
            dst.append(obj)
            dst.set_focus(len(dst) - 1)
        else:
            dst.insert(0, obj)
            dst.set_focus(0)

    # [ BUTTONS ]
    def button(self, button_text, fn, b=False, data=None):
        """
        Adds button, with border if needed
        :t: str(text)
        :fn: function(callback)
        :b: bool(default:false)
        """
        w = urwid.Button(button_text, on_press=fn, user_data=data)
        w = urwid.AttrMap(w, 'button normal', 'button select')
        if type(b) == str:
            w = urwid.LineBox(w, title=b)
        if b == True:
            w = urwid.LineBox(w)
        return w

    def btn_create_zpool(self, w):
        self.log_it(u"Create zpool window opened")
        self._popup_target.open_box(self.panel_render(u"Create zpool", [], 'zpool'))

    def btn_edit_zpool(self, button, pool_name):
        self.log_it(u"Edit zpool {}".format(pool_name))
        window_title = ' '.join([pool_name, 'properties'])
        self._popup_target.open_box(self.popup_layout(), window_title)

    def btn_create_zfs(self, w):
        self.log_it(u"Create zfs filesystem")
        window_title = 'Create new ZFS filesystem.'
        self._popup_target.open_box(self.panel_render(False, [], 'zfs'), window_title)

    def btn_import(self, w):
        self.log_it(u"Clear zpools")
        self.handle['zlist'].clear()

    def exit_program(self, w):
        raise urwid.ExitMainLoop()

    def fn_del(self):
        if True:
            print('True!')

    def create_edit(self, label, text, fn):
        w = urwid.Edit(label, text)
        urwid.connect_signal(w, 'change', fn)
        fn(w, text)
        w = urwid.AttrWrap(w, 'edit')
        return w

    def edit_change_event(self, widget, text):
        pass

    # [ ALL GUI PARTS ]
    def popup_layout(self):
        top_section = urwid.Columns([
                ('weight', 2, urwid.Text('Checkboxes here')),
                ('weight', 2, urwid.Text('something more'))
            ])
        self.do_del = self.create_edit('Type "yes"', '', self.edit_change_event)
        button_section = urwid.GridFlow([
                urwid.LineBox(self.do_del),
                self.button('Delete', self.fn_del, True ),
                self.button('Edit', self.fn_del, True ),
                self.button('Apply', self.fn_del, True ),
                self.button('Cancel', self._popup_target.keypress, True, 'esc' )
            ], 17, 2, 0, 'center')
        w = [top_section, self.hd, button_section]
        w = urwid.SimpleFocusListWalker(w)
        w = urwid.ListBox(w)
        return w

    def log_window(self):
        """
        This creates log window. Also adds bottom captions.
        :return: urwid.[widget]
        """
        log_head = urwid.AttrMap(urwid.Text(u'Log'), 'header', 'fheader')   # Header
        log_foot = urwid.AttrMap(urwid.Text(u'F5 - force refresh data | q - exit', align='right'), 'header')
        self.log_box = urwid.SimpleFocusListWalker(self.log)                # Window content
        w = urwid.ListBox(self.log_box)
        w = urwid.Frame(w, header=log_head, footer=log_foot )               # BoxWidget
        return w

    def panel_render(self, header, widget_list, slot):
        """
        Render empty pannel, that can be filled with happiness :)
        :header: str()
        :widget_list: list[]
        :slot: str - name of handle slot
        """
        if header:
            h = urwid.AttrMap(urwid.Text(header, align='center'), 'header', 'fheader')
            widget_list.insert(0, h)
        self.handle[slot] = urwid.SimpleFocusListWalker(widget_list)
        w = urwid.ListBox(self.handle[slot])
        return w

    def frame_top_render(self):
        """
        Render top frame for widgets. Three separate columns.
        :return: urwid[widget]
        """
        w = urwid.Columns([
            ('weight', 2, self.panel_render(u'Disks in system', [], 'dlist')),
            ('fixed', 1, self.vd),
            ('weight', 2, self.panel_render(u'ZPools (Press to interact)', [], 'zlist')),
            ('fixed', 1, self.vd),
            ('weight', 2, self.panel_render(u'Main menu', self.model.button_menu(), 'mlist'))
        ])
        return w

    def popup_frame(self):
        """
        Popup frame.
        :return: urwid[widget]
        """
        w = urwid.Columns([
            ('weight', 2, urwid.Text('Left panel')),
            ('fixed', 1, self.vd),
            ('weight', 1, urwid.Text('Menu here'))
        ])
        return w

    def frame_refresh(self, widget_list, slot):
        """
        Refreshes data on panel
        :widget_list: [] data to be refreshed
        :slot: str - name of handle
        """
        current_title = self.handle[slot][0]
        self.handle[slot].clear()
        self.handle[slot].append(current_title)
        for item in widget_list:
            self.handle[slot].append(item)

    def main_frame(self):
        """
        Initial frame render
        :return: urwid[widget]
        """
        self.hor_frame = urwid.Pile([
            ('weight', 3, self.frame_top_render()),
            ('weight', 1, self.log_window())
        ])
        #w[1]._selectable = False                                    # Prohibit selecting log window
        
        # [ BACKGROUND ]
        w = urwid.AttrMap(self.hor_frame, 'body')
        w = urwid.LineBox(w, title='ZFS Disk Utility. Detected OS family: '+self._system_update.os)
        w = urwid.AttrMap(w, 'line')
        w = self.main_shadow(w)
        return w

    def init_window(self):
        """
        Start uxwid framework part with loop.
        """
        self.model = ZfsGuiModel(self)
        self._bottom_frame_with_shadow = self.main_frame()
        self._popup_target = CascadingBoxes(self._bottom_frame_with_shadow)
        self._loop = urwid.MainLoop(self._popup_target, self.palette, unhandled_input=self.grab_input)
        self.frame_refresh(self.model.disk_list(self.mothership_core.list_disks()), 'dlist')
        self.frame_refresh(self.model.zfs_pools(self.mothership_core.list_zpools()), 'zlist')
        self._loop.run()


if __name__ == '__main__':

    gui = ZfsGui()
    #x = ZfsDrive()

    #print(x.list_zpools())
    #print(x.create_pool('miraid', ['/dev/sdb2', '/dev/sdb3'], 'Mirror', True))
    #print(x.create_pool('z2raid', ['/dev/sdb4', '/dev/sdb5', '/dev/sdb6'], 'RAID-Z L1', True))
    #print(x.show_pools()[0])
    # print(x.delete_pool('tank')[0])
    # print(x.show_pools()[0])
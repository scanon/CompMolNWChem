# -*- coding: utf-8 -*-
import os
import time
import unittest
from configparser import ConfigParser
import shutil
import requests

from unittest.mock import patch

from CompMolNWChem.CompMolNWChemImpl import CompMolNWChem
from CompMolNWChem.CompMolNWChemServer import MethodContext
from CompMolNWChem.authclient import KBaseAuth as _KBaseAuth

from installed_clients.specialClient import special
from installed_clients.WorkspaceClient import Workspace

def fake_get(uri, headers=None):
    class resp:
        def __init__(self, data): 
            self.text = data
            self.status_code = 200

    inpath = '/kb/module/test/test_compounds.tsv'
    with open(inpath) as f:
        data = f.read()
    return resp(data)


class CompMolNWChemTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('CompMolNWChem'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'CompMolNWChem',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = Workspace(cls.wsURL)
        cls.serviceImpl = CompMolNWChem(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_ContigFilter_" + str(suffix)
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    def getContext(self):
        return self.__class__.ctx
    
    def getWsClient(self):
        return self.__class__.wsClient

    def getWsId(self):
        if hasattr(self.__class__, 'wsId'):
            return self.__class__.wsId
        suffix = int(time.time() * 1000)
        wsName = "test_CompoundSetUtils_" + str(suffix)
        ret = self.getWsClient().create_workspace({'workspace': wsName})  # noqa
        self.__class__.wsId = ret[0]
        return ret[0]

    def getImpl(self):
        return self.__class__.serviceImpl
    
    @staticmethod
    def fake_slurm(params):
        shutil.rmtree('/kb/module/work/tmp/simulation/')
        shutil.copytree('/kb/module/test/results/', '/kb/module/work/tmp/simulation/')
        return {'bogus': None}
    
    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa

    @patch('requests.get', side_effect=fake_get)
    def xtest_nwchem(self, mock_get):
        shutil.rmtree('/kb/module/work/tmp/', ignore_errors=True)
        os.mkdir('/kb/module/work/tmp')
        params = {'workspace_name': self.wsName,
                  'workspace_id': self.getWsId(),
                  'Input_File': 'test_compounds.tsv',
                  'calculation_type': 'energy'}
        ret = self.getImpl().run_CompMolNWChem(self.getContext(), params)[0]
        assert ret and ('report_name' in ret)

    @patch.object(special, "slurm",
                  new=fake_slurm)
    @patch('requests.get', side_effect=fake_get)
    def test_nwchem_hpc(self, mock_get):
        shutil.rmtree('/kb/module/work/tmp/', ignore_errors=True)
        os.mkdir('/kb/module/work/tmp')
        params = {'workspace_name': self.wsName,
                  'workspace_id': self.getWsId(),
                  'Input_File': 'test_compounds.tsv',
                  'calculation_type': 'energy'}
        ret = self.getImpl().run_CompMolNWChem_hpc(self.getContext(), params)[0]
        assert ret and ('report_name' in ret)

#    def test_your_method(self):

#        ret = self.serviceImpl.run_CompMolNWChem(self.ctx, {'workspace_name': self.wsName,'workspace_id':self.getWsId(),
#                                                                 'Input_File':'test_compounds.tsv','calculation_type':'energy'})

#        print("Output")
#        print (ret)

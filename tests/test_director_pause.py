#!/usr/bin/env python3
"""A Director-paused card cannot get a new lease, even from its previous owner."""
from pathlib import Path
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

CLI=Path(__file__).resolve().parents[1]/'bin/chatcode'

class DirectorPause(unittest.TestCase):
    def test_owner_and_stranger_refused_but_normal_jobs_still_claim(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as home:
            root=Path(td)
            env=dict(os.environ,HOME=home)
            def run(who,*args):
                return subprocess.run([sys.executable,str(CLI),'--local',str(root),'--agent',who,*args],env=env,capture_output=True,text=True,timeout=30)
            for who in ('alice','bob'):
                p=run(who,'init','--quiet','--model','mock','--role','worker')
                self.assertEqual(p.returncode,0,p.stderr)
            p=run('alice','tasks','new','paused fixture')
            self.assertEqual(p.returncode,0,p.stderr)
            tid=re.search(r't-\d{8}-[a-f0-9]{4}',p.stdout).group(0)
            self.assertEqual(run('alice','tasks','claim',tid).returncode,0)
            path=root/'board/tasks'/f'{tid}.json'
            task=json.loads(path.read_text())
            task['status']='blocked';task['lease']=None
            task['director_pause']={'reason':'Director explicitly paused this project','resume_status':'claimed'}
            path.write_text(json.dumps(task))
            before=path.read_bytes()
            for who in ('alice','bob'):
                p=run(who,'tasks','claim',tid)
                self.assertNotEqual(p.returncode,0)
                self.assertIn('paused by the Director',p.stdout+p.stderr)
                self.assertEqual(path.read_bytes(),before)
            p=run('alice','tasks','heartbeat',tid,'--note','cannot extend a paused task')
            self.assertNotEqual(p.returncode,0)
            self.assertIn('paused by the Director',p.stdout+p.stderr)
            self.assertEqual(path.read_bytes(),before)
            p=run('alice','tasks','release',tid)
            self.assertEqual(p.returncode,0,p.stderr)
            released=json.loads(path.read_text())
            self.assertEqual(released['status'],'blocked')
            self.assertIsNone(released['owner'])
            self.assertTrue(released['director_pause'])
            p=run('alice','tasks','new','active video fixture')
            newtid=re.search(r't-\d{8}-[a-f0-9]{4}',p.stdout).group(0)
            self.assertEqual(run('bob','tasks','claim',newtid).returncode,0)

if __name__=='__main__':unittest.main(verbosity=2)

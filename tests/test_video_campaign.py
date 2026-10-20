#!/usr/bin/env python3
"""Contract tests for the 15-job campaign. These do NOT claim films exist."""
from pathlib import Path
import json
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT/'projects/youtube-training'

class VideoCampaign(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=json.loads((PROJECT/'campaign.json').read_text())
        cls.jobs={j['task_id']:j for j in cls.c['jobs']}

    def test_fifteen_substantial_jobs_ten_productions_and_one_screening(self):
        jobs=self.c['jobs']
        self.assertEqual(len(jobs),15)
        self.assertEqual(len({j['task_id'] for j in jobs}),15)
        self.assertEqual(sum(j['role']=='shared' for j in jobs),4)
        self.assertEqual(sum(j['role']=='production' for j in jobs),10)
        self.assertEqual(sum(j['role']=='screening' for j in jobs),1)
        for j in jobs:
            card=json.loads((ROOT/'board/tasks'/f"{j['task_id']}.json").read_text())
            self.assertIn('video-training',card['tags'])
            self.assertIn('youtube',card['tags'])
            self.assertGreater(len(card['desc']),1500)
            self.assertIn('Multi-shift job',card['desc'])
            self.assertIn('ESTIMATED EFFORT',card['desc'])
            self.assertIn('DELIVER',card['desc'])
            self.assertIn('storagecode',card['desc'])
            self.assertEqual(card['deps'],j['dependencies'])

    def test_room_tag_filter_returns_only_this_campaign_not_the_whole_board(self):
        proc=subprocess.run([sys.executable,str(ROOT/'bin/chatcode'),'--local',str(ROOT),'--agent','vesta','tasks','list','--status','open','--tags','video-training,yt-training-s1','--json'],capture_output=True,text=True,timeout=30)
        self.assertEqual(proc.returncode,0,proc.stderr)
        listed=json.loads(proc.stdout)
        expected=set()
        for j in self.c['jobs']:
            card=json.loads((ROOT/'board/tasks'/f"{j['task_id']}.json").read_text())
            if card['status']=='open':expected.add(card['id'])
        self.assertEqual({t['id'] for t in listed},expected)
        self.assertTrue(all('video-training' in t['tags'] and 'yt-training-s1' in t['tags'] for t in listed))

    def test_real_five_minute_target_in_english(self):
        c=self.c
        self.assertEqual(c['language'],'en')
        self.assertGreaterEqual(c['required_final_videos'],10)
        self.assertEqual(c['min_video_seconds'],300)
        self.assertEqual(c['max_video_seconds'],330)
        self.assertGreaterEqual(c['min_total_seconds'],3000)
        self.assertEqual(c['canonical_archive'],'dreamer2664/storagecode')
        slots=c['slots']
        self.assertEqual({s['id'] for s in slots},{f'YT{i:02d}' for i in range(1,11)})
        self.assertEqual(len({s['production_task_id'] for s in slots}),10)
        for s in slots:
            self.assertTrue((PROJECT/s['working_project']/'README.md').is_file())
            self.assertTrue(s['delivery_manifest'].startswith('storagecode/data/youtube-training/'))

    def test_dependency_graph_has_no_cycle_and_screening_requires_all_ten(self):
        def visit(tid,path):
            self.assertNotIn(tid,path)
            self.assertIn(tid,self.jobs)
            for dep in self.jobs[tid]['dependencies']:visit(dep,path+[tid])
        for tid in self.jobs:visit(tid,[])
        final=next(j for j in self.c['jobs'] if j['role']=='screening')
        production={j['task_id'] for j in self.c['jobs'] if j['role']=='production'}
        self.assertEqual(set(final['dependencies']),production)

    def test_templates_route_to_one_archive_and_keep_universal_clean_key_block(self):
        # v4: there is exactly one law file; every other manual is a stub or archived.
        d=(ROOT/'AGENCY.md').read_text()
        self.assertEqual(d.count('=PENDING-ISSUE'),2)
        self.assertIn('KIT-DBF340',d)
        self.assertIn('storagecode',d)
        self.assertNotIn('git clone https://github.com/dreamer2664/storage\n',d)
        self.assertIn('OUTPOST MARS is paused',d)
        self.assertIn('fewer than TEN actual accepted',(PROJECT/'JOBS.md').read_text()+(PROJECT/'ACCEPTANCE.md').read_text()+(ROOT/'board/tasks'/f"{next(j['task_id'] for j in self.c['jobs'] if j['role']=='screening')}.json").read_text())

if __name__=='__main__':unittest.main(verbosity=2)

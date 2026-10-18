#!/usr/bin/env python3
"""Audit the active authorial Start chapter, its preserved IDs and Prism copy."""
import sys
import tomllib
from pathlib import Path
import re,json,copy,shutil,datetime
class Raw(str): pass
class Parser:
 def __init__(self,s): self.t=re.findall(r'"(?:\\.|[^"\\])*"|[{}\[\]:,]|[^\s{}\[\]:,]+',re.sub(r'(?m)^\s*//.*$','',s)); self.i=0
 def pop(self): t=self.t[self.i]; self.i+=1; return t
 def value(self):
  t=self.pop()
  if t=='{':
   d={}
   while self.t[self.i]!='}':
    k=self.pop(); k=json.loads(k) if k.startswith('"') else k
    assert self.pop()==':'
    assert k not in d
    d[k]=self.value()
    if self.t[self.i]==',': self.pop()
   self.pop(); return d
  if t=='[':
   a=[]
   while self.t[self.i]!=']':
    a.append(self.value())
    if self.t[self.i]==',':self.pop()
   self.pop(); return a
  return json.loads(t) if t.startswith('"') else Raw(t)
 def parse(self):
  d=self.value(); assert self.i==len(self.t); return d


import hashlib,itertools,math,argparse

def audit():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--prism',type=Path,default=Path.home()/'.local/share/PrismLauncher/instances/GTIA (full pack)/minecraft/config/ftbquests/quests')
 ap.add_argument('--check-prism',action='store_true',help='also require the installed copy to be byte-identical to the source')
 args=ap.parse_args()
 pack=Path(__file__).resolve().parents[1]
 source=pack/'config/ftbquests/quests'
 backup=pack/'quests-src/start-author-2026-09-30'
 d=Parser((source/'chapters/start.snbt').read_text()).parse()
 # D-291: the Start is split into Welcome and Start; both hold the author's quests.
 w=Parser((source/'chapters/welcome.snbt').read_text()).parse()
 chapter_of={q['id']:'start' for q in d['quests']}|{q['id']:'welcome' for q in w['quests']}
 d['quests']=d['quests']+w['quests']
 old=Parser((backup/'chapters/start.snbt').read_text()).parse()
 qs={q['id']:q for q in d['quests']}
 mq=Parser((source/'chapters/modes.snbt').read_text()).parse()['quests']; modes={q['id'] for q in mq}; journey_id=mq[0]['id']
 mode_of=lambda q:next((m for m in q.get('dependencies',[]) if m in modes),None)
 kits={q['id']:q for q in qs.values() if mode_of(q)}  # Starting Kits per mode (GTIA-D-279)
 # The Journey kit of each Start step (start.toml [[mode_reward]]) carries the author's original rewards.
 sys.path.insert(0,str(pack/'tools')); from questgen import ident
 by_title={q.get('title'):q['id'] for q in Parser((pack/'quests-src/start.original.snbt').read_text()).parse()['quests']}
 kit_of={by_title[s['title']]:ident(f"quest:start:{s['key']}_journey") for s in tomllib.loads((pack/'quests-src/start.toml').read_text())['mode_reward']}
 assert {q['id'] for q in old['quests']}<=set(qs) and len(old['quests'])==29  # the 29 approved quests (The Research Tree was removed with GTIA-D-226)
 ids=[d['id'],w['id']]
 for q in qs.values():
  ids.append(q['id'])
  assert q['title'] and q['subtitle'] and q['icon']
  assert len(q['subtitle'])<=70
  assert any(q['description']) and all(isinstance(t,str) and t.isascii() for t in q['description'])
  assert all((dep in qs or dep in modes) and dep!=q['id'] for dep in q.get('dependencies',[]))
  assert q['tasks']
  for t in q['tasks']:
   ids.append(t['id']);assert t['title']
   if t['type']=='item':
    assert t['consume_items']=='false' and t['match_nbt']=='false'
    assert isinstance(t['item'],str) and ':' in t['item']
   else:assert t['type']=='checkmark'
  ids.extend(r['id'] for r in q.get('rewards',[]))
  for axis in ['x','y']:assert float(str(q[axis]).rstrip('d'))*4%1==0
 assert len(ids)==len(set(ids)), 'Duplicate object ID'
 visiting=set();visited=set()
 def visit(i):
  assert i not in visiting,'Dependency cycle'
  if i in visited:return
  visiting.add(i)
  for dep in qs[i].get('dependencies',[]):
   if dep in qs:visit(dep)
  visiting.remove(i);visited.add(i)
 for i in qs:visit(i)
 def number(q,k):return float(str(q[k]).rstrip('d'))
 for a,b in itertools.combinations(qs.values(),2):
  if mode_of(a) and mode_of(b) and mode_of(a)!=mode_of(b):continue
  if chapter_of[a['id']]!=chapter_of[b['id']]:continue
  assert math.hypot(number(a,'x')-number(b,'x'),number(a,'y')-number(b,'y'))>(number(a,'size')+number(b,'size'))/2, 'Overlapping nodes'
 for a in old['quests']:
  b=qs[a['id']]
  assert {t['id'] for t in a['tasks']}=={t['id'] for t in b['tasks']}
  if any(r['type']=='item' for r in a.get('rewards',[])):
   journey=[kits[kit_of[a['id']]]] if kit_of.get(a['id']) in kits else []
   assert a['rewards']==b['rewards'] or (not b['rewards'] and journey and journey[0]['rewards']==a['rewards']),'Author item reward changed'
 # The main route must be reachable without the optional branches.
 gate=qs['64D91166C361698D'];ancestors=set()
 def collect(i):
  for dep in qs[i].get('dependencies',[]):
   if dep not in ancestors:ancestors.add(dep);collect(dep)
 collect(gate['id'])
 assert gate['tasks'][0]['item']=='gtceu:coke_gem'
 assert '01780714D3006B80' in ancestors and '487911F0F530BC5C' in ancestors
 assert not ancestors.intersection({'44B99A5358D9A1A0','5ACCF4B9A48CCFFB','6B586DEF6A83F004','79F9D0A994CF9EDB','4B0F76331F09E588','75F8535E4B2326CE'})
 for rel in ['chapters/start.snbt','chapters/welcome.snbt','data.snbt','chapter_groups.snbt']:
  Parser((source/rel).read_text()).parse()
  if args.check_prism:assert (source/rel).read_bytes()==(args.prism/rel).read_bytes(),f'Prism mismatch: {rel}'
 print(f'Start OK: {len(qs)} quests, {len(ids)} unique chapter/quest/task/reward IDs, no cycles or overlaps; titles, descriptions, icons and preserved item rewards.')
 print('start.snbt SHA-256:',hashlib.sha256((source/'chapters/start.snbt').read_bytes()).hexdigest())

if __name__=='__main__':audit()

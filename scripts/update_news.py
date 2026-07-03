#!/usr/bin/env python3
import json, re, hashlib, html, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

ROOT=Path(__file__).resolve().parents[1]
FEEDS=[
 ('ABC News','https://abcnews.go.com/abcnews/usheadlines'),
 ('ABC Video','https://abcnews.go.com/abcnews/video'),
 ('NBC News','https://feeds.nbcnews.com/nbcnews/public/news'),
 ('CNN','http://rss.cnn.com/rss/cnn_us.rss'),
 ('CBS News','https://www.cbsnews.com/latest/rss/us/'),
 ('NPR','https://feeds.npr.org/1001/rss.xml'),
]
UA='DailyNewsEnglish/1.0 (+https://github.com/www0815/us-news-english-learning)'

def txt(node, names):
 for name in names:
  e=node.find(name)
  if e is not None and e.text: return e.text.strip()
 return ''
def clean(s):
 s=html.unescape(re.sub(r'<[^>]+>',' ',s or ''))
 return re.sub(r'\s+',' ',s).strip()
def date(s):
 try:
  d=parsedate_to_datetime(s)
  if not d.tzinfo:d=d.replace(tzinfo=timezone.utc)
  return d.astimezone(timezone.utc).isoformat()
 except:return datetime.now(timezone.utc).isoformat()
def fetch(source,url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, application/xml, text/xml'})
 with urllib.request.urlopen(req,timeout=25) as r: raw=r.read()
 root=ET.fromstring(raw); items=[]
 nodes=root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
 for n in nodes[:35]:
  title=clean(txt(n,['title','{http://www.w3.org/2005/Atom}title']))
  link=txt(n,['link'])
  if not link:
   le=n.find('{http://www.w3.org/2005/Atom}link'); link=le.get('href','') if le is not None else ''
  summary=clean(txt(n,['description','summary','{http://www.w3.org/2005/Atom}summary','{http://purl.org/rss/1.0/modules/content/}encoded']))
  published=txt(n,['pubDate','published','updated','{http://www.w3.org/2005/Atom}published','{http://www.w3.org/2005/Atom}updated'])
  media_url='';media_type=''
  for e in list(n):
   tag=e.tag.lower();typ=e.get('type','').lower();u=e.get('url','') or e.get('href','')
   if u and ('enclosure' in tag or 'content' in tag):
    if 'audio' in typ or re.search(r'\.(mp3|m4a)(\?|$)',u,re.I):media_url,media_type=u,'audio';break
    if 'video' in typ or re.search(r'\.(mp4|m3u8)(\?|$)',u,re.I):media_url,media_type=u,'video';break
  if not media_type and re.search(r'\b(video|watch)\b',title+' '+link,re.I):media_type='video'
  transcript=bool(re.search(r'\btranscript\b',title+' '+summary+' '+link,re.I))
  if title and link:
   items.append({'id':hashlib.sha1(link.encode()).hexdigest()[:14],'source':source,'title':title,'summary':summary[:900],'link':link,'published':date(published),'mediaType':media_type,'mediaUrl':media_url,'transcript':transcript,'transcriptUrl':link if transcript else ''})
 return items

def main():
 all_items=[];ok=[];errors=[]
 for source,url in FEEDS:
  try:
   got=fetch(source,url);all_items+=got
   if got:ok.append(source)
  except Exception as e:errors.append(f'{source}: {e}')
 seen=set();unique=[]
 for x in sorted(all_items,key=lambda z:z['published'],reverse=True):
  key=re.sub(r'\W+','',x['title'].lower())[:80]
  if key not in seen:seen.add(key);unique.append(x)
 payload={'date':datetime.now(timezone.utc).date().isoformat(),'updatedAt':datetime.now(timezone.utc).isoformat(),'sources':ok,'errors':errors,'items':unique[:120]}
 data=ROOT/'data';archive=data/'archive';archive.mkdir(parents=True,exist_ok=True)
 (data/'news.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 (archive/f"{payload['date']}.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
 cutoff=datetime.now(timezone.utc).date()-timedelta(days=365)
 for f in archive.glob('*.json'):
  try:
   if datetime.strptime(f.stem,'%Y-%m-%d').date()<cutoff:f.unlink()
  except:pass
 print(f"Saved {len(payload['items'])} stories from {len(ok)} sources; errors={errors}")
if __name__=='__main__':main()

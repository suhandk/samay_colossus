"""One-shot CSV refresh suitable for cron or Windows Task Scheduler."""
import argparse,json,time
from pathlib import Path
from urllib.parse import urlparse
import httpx
from .db import Session
from .ingest import ingest,utcnow

def download(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or not (parsed.hostname or '').endswith('.gov.in'):raise ValueError('Reviewed government HTTPS CSV URL required')
    for attempt in range(3):
        try:
            with httpx.Client(timeout=30,follow_redirects=False) as client:
                with client.stream('GET',url) as response:
                    response.raise_for_status()
                    chunks=[];size=0
                    for chunk in response.iter_bytes():
                        size+=len(chunk)
                        if size>20_000_000:raise ValueError('CSV exceeds 20 MB; split historical export')
                        chunks.append(chunk)
                    content=b''.join(chunks).decode('utf-8-sig')
                    if content.lstrip().startswith('<'):raise ValueError('Expected CSV, received HTML')
                    return content
        except (httpx.TimeoutException,httpx.NetworkError):
            if attempt==2:raise RuntimeError('Source network unavailable') from None
            time.sleep(2**attempt)
        except httpx.HTTPStatusError as error:
            if error.response.status_code not in (429,500,502,503,504) or attempt==2:raise RuntimeError('Source HTTP failure: '+str(error.response.status_code)) from None
            time.sleep(2**attempt)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('manifest');args=parser.parse_args()
    manifest=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    try:
        content=download(manifest['download_url']);manifest['retrieved_at']=utcnow().isoformat()
        with Session.begin() as db:result=ingest(db,content,manifest)
        print(json.dumps({'event':'refresh_completed',**result}))
    except Exception as error:
        print(json.dumps({'event':'refresh_failed','error_type':type(error).__name__,'at':utcnow().isoformat()}))
        raise SystemExit(1)
if __name__=='__main__':main()

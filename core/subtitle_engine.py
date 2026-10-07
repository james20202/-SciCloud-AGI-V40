import os, json, re
from core.config import PROJECT_DIR

class SubtitleEngine:
    def __init__(self): self.root=os.path.join(PROJECT_DIR,'subtitles'); os.makedirs(self.root,exist_ok=True)
    def _time(self, sec):
        ms=int(round(sec*1000)); h=ms//3600000; ms%=3600000; m=ms//60000; ms%=60000; s=ms//1000; ms%=1000
        return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
    def to_srt(self, segments, output):
        os.makedirs(os.path.dirname(output) or self.root,exist_ok=True)
        with open(output,'w',encoding='utf-8') as f:
            for i,x in enumerate(segments,1):
                start=float(x.get('start',0)); end=float(x.get('end',start+2)); text=str(x.get('text','')).strip()
                if not text: continue
                f.write(f'{i}\n{self._time(start)} --> {self._time(end)}\n{text}\n\n')
        return output if os.path.isfile(output) else None
    def from_dialogue(self, dialogue, output):
        seg=[]; t=0
        for item in dialogue or []:
            text=item.get('text','') if isinstance(item,dict) else str(item)
            dur=max(1.2,min(8.0,len(text)*0.18)); seg.append({'start':t,'end':t+dur,'text':text}); t+=dur
        return self.to_srt(seg,output)
subtitle_engine=SubtitleEngine()

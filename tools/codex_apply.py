#!/usr/bin/env python3
"""Apply a Codex apply_patch envelope to a tree (Update/Add/Delete File)."""
import sys, os
def parse(text):
    lines = text.split('\n')
    assert lines[0].strip() == '*** Begin Patch', lines[0]
    ops=[]; i=1
    while i < len(lines):
        l=lines[i]
        if l.startswith('*** End Patch'): break
        if l.startswith('*** Add File: '):
            path=l[14:]; body=[]; i+=1
            while i<len(lines) and not lines[i].startswith('*** '):
                body.append(lines[i][1:]); i+=1
            ops.append(('add',path,body)); continue
        if l.startswith('*** Delete File: '):
            ops.append(('del',l[17:],None)); i+=1; continue
        if l.startswith('*** Update File: '):
            path=l[17:]; i+=1; move=None
            if i<len(lines) and lines[i].startswith('*** Move to: '): move=lines[i][13:]; i+=1
            hunks=[]; cur=None
            while i<len(lines) and not (lines[i].startswith('*** ') and not lines[i].startswith('*** End of File')):
                s=lines[i]
                if s.startswith('@@'):
                    cur={'anchor':s[2:].strip(),'lines':[],'eof':False}; hunks.append(cur)
                elif s.startswith('*** End of File'):
                    cur['eof']=True
                else:
                    if cur is None: cur={'anchor':'','lines':[],'eof':False}; hunks.append(cur)
                    if s=='' : cur['lines'].append((' ',''))
                    else: cur['lines'].append((s[0],s[1:]))
                i+=1
            ops.append(('upd',path,(hunks,move))); continue
        if l.strip()=='' : i+=1; continue
        raise SystemExit(f'bad line {i}: {l!r}')
    return ops
def find(hay, needle, start, eof):
    for norm in (lambda x:x, lambda x:x.rstrip(), lambda x:x.strip()):
        n=[norm(x) for x in needle]
        rng = [len(hay)-len(needle)] if eof else range(start, len(hay)-len(needle)+1)
        for k in rng:
            if k<start: continue
            if [norm(x) for x in hay[k:k+len(needle)]]==n: return k
    return -1
def apply(root, text, strip):
    for kind,path,data in parse(text):
        rel=path[len(strip):] if path.startswith(strip) else path
        fp=os.path.join(root,rel)
        if kind=='add':
            os.makedirs(os.path.dirname(fp) or '.',exist_ok=True)
            open(fp,'w').write('\n'.join(data)+'\n'); continue
        if kind=='del': os.remove(fp); continue
        hunks,move=data
        content=open(fp).read()
        trailing=content.endswith('\n')
        hay=content.split('\n')
        if trailing: hay=hay[:-1]
        pos=0
        for h in hunks:
            if h['anchor']:
                a=find(hay,[h['anchor']],pos,False)
                if a<0: raise SystemExit(f'{rel}: anchor not found {h["anchor"]!r}')
                pos=a+1
            old=[t for c,t in h['lines'] if c in ' -']
            new=[t for c,t in h['lines'] if c in ' +']
            if not old:
                k=len(hay) if h['eof'] else pos
            else:
                k=find(hay,old,pos,h['eof'])
                if k<0:
                    raise SystemExit(f'{rel}: hunk not found:\n'+'\n'.join(old[:12]))
            hay[k:k+len(old)]=new; pos=k+len(new)
        out='\n'.join(hay)+('\n' if trailing or True else '')
        if move:
            mrel=move[len(strip):] if move.startswith(strip) else move
            os.remove(fp); fp=os.path.join(root,mrel)
        open(fp,'w').write(out)
        print('updated',rel)
if __name__=='__main__':
    root,strip=sys.argv[1],sys.argv[2]
    for pf in sys.argv[3:]:
        print('#',pf); apply(root,open(pf).read(),strip)

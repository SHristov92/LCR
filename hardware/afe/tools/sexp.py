import re
def parse(s):
    tok=re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')
    stack=[[]]
    for m in tok.finditer(s):
        t=m.group(0)
        if t=='(':
            stack.append([])
        elif t==')':
            x=stack.pop(); stack[-1].append(x)
        else:
            stack[-1].append(t)
    return stack[0]
def dump(x,ind=0):
    if isinstance(x,list):
        if all(not isinstance(e,list) for e in x) and len(' '.join(x))<100:
            return '('+' '.join(x)+')'
        parts=[dump(e,ind+1) for e in x]
        out='('+parts[0]
        for p in parts[1:]:
            out+='\n'+'  '*(ind+1)+p
        return out+')'
    return x
_cache={}
def lib(name):
    if name not in _cache:
        _cache[name]=parse(open(f'/usr/share/kicad/symbols/{name}.kicad_sym').read())[0]
    return _cache[name]
def find_sym(libname,sym):
    L=lib(libname)
    for e in L:
        if isinstance(e,list) and e[0]=='symbol' and e[1]=='"%s"'%sym:
            return e
    raise KeyError(sym)
def pins(sym_node, libname=None):
    res=[]
    def walk(n,unit):
        for e in n:
            if isinstance(e,list):
                if e[0]=='symbol':
                    m=re.match(r'"(.*)_(\d+)_(\d+)"',e[1]); walk(e,int(m.group(2)) if m else unit)
                elif e[0]=='pin':
                    at=[x for x in e if isinstance(x,list) and x[0]=='at'][0]
                    ln=[x for x in e if isinstance(x,list) and x[0]=='length'][0]
                    nm=[x for x in e if isinstance(x,list) and x[0]=='name'][0][1].strip('"')
                    num=[x for x in e if isinstance(x,list) and x[0]=='number'][0][1].strip('"')
                    hidden='hide' in e
                    res.append(dict(unit=unit,type=e[1],name=nm,num=num,x=float(at[1]),y=float(at[2]),rot=float(at[3]) if len(at)>3 else 0,len=float(ln[1]),hide=hidden))
    walk(sym_node,0)
    return res

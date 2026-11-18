import sys,csv,collections,re,os;sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from sexp import parse
n=parse(open(sys.argv[1]).read())[0]
comps=[e for e in n if isinstance(e,list) and e[0]=='components'][0][1:]
def f(c,k):
    r=[x for x in c if isinstance(x,list) and x[0]==k]
    return r[0][1].strip('"') if r else ''
g=collections.OrderedDict()
for c in comps:
    lib=[x for x in c if isinstance(x,list) and x[0]=='libsource'][0]
    part=[y for y in lib if isinstance(y,list) and y[0]=='part'][0][1].strip('"')
    g.setdefault((f(c,'value'),part,f(c,'footprint')),[]).append(f(c,'ref'))
key=lambda r:(re.match(r'\D+',r).group(0),int(re.search(r'\d+',r).group(0)))
with open(sys.argv[2],'w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['Qty','References','Value','Symbol','Footprint'])
    for (val,part,fp),refs in sorted(g.items(),key=lambda kv:key(sorted(kv[1],key=key)[0])):
        w.writerow([len(refs),' '.join(sorted(refs,key=key)),val,part,fp])

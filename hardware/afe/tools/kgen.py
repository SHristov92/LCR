"""Tiny KiCad 7 schematic generator: places library symbols and connects every
pin with a short wire stub ending in a net label / power symbol / no-connect."""
import copy, re, uuid as _uuid
from sexp import parse, dump, lib, find_sym

PROJECT = "LCR_AFE"
U = lambda: str(_uuid.uuid4())

def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

# ---------------------------------------------------------------- library
CUSTOM = {}          # name -> sexp node (top level symbol) for LCR lib

def lib_node(lib_id):
    libname, sym = lib_id.split(':')
    if libname == 'LCR':
        return copy.deepcopy(CUSTOM[sym])
    n = copy.deepcopy(find_sym(libname, sym))
    ext = [e for e in n if isinstance(e, list) and e[0] == 'extends']
    if ext:
        parent_name = ext[0][1].strip('"')
        p = copy.deepcopy(find_sym(libname, parent_name))
        props = [e for e in n if isinstance(e, list) and e[0] == 'property']
        out = [p[0], q(sym)]
        for e in p[2:]:
            if isinstance(e, list) and e[0] == 'property':
                continue
            if isinstance(e, list) and e[0] == 'symbol':
                e[1] = e[1].replace('"' + parent_name + '_', '"' + sym + '_')
                out.append(e)
            elif isinstance(e, list) and e[0] == 'extends':
                continue
            else:
                out.append(e)
        # insert child properties before sub-symbols
        idx = next(i for i, e in enumerate(out) if isinstance(e, list) and e[0] == 'symbol')
        out[idx:idx] = props
        n = out
    return n

def embedded(lib_id):
    n = lib_node(lib_id)
    n[1] = q(lib_id)
    return n

def sym_pins(lib_id, unit):
    n = lib_node(lib_id)
    res = []
    for e in n:
        if isinstance(e, list) and e[0] == 'symbol':
            m = re.match(r'"(.*)_(\d+)_(\d+)"', e[1])
            u, c = int(m.group(2)), int(m.group(3))
            if c not in (0, 1) or u not in (0, unit):
                continue
            for p in e:
                if isinstance(p, list) and p[0] == 'pin':
                    at = [x for x in p if isinstance(x, list) and x[0] == 'at'][0]
                    num = [x for x in p if isinstance(x, list) and x[0] == 'number'][0][1].strip('"')
                    res.append(dict(num=num, type=p[1], x=float(at[1]), y=float(at[2]),
                                    rot=float(at[3]) if len(at) > 3 else 0, hide='hide' in p))
    return res

def props_of(lib_id):
    n = lib_node(lib_id)
    out = {}
    for e in n:
        if isinstance(e, list) and e[0] == 'property':
            at = [x for x in e if isinstance(x, list) and x[0] == 'at'][0]
            out[e[1].strip('"')] = (e[2].strip('"'), float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0, 'hide' in str(e))
    return out

def is_power_lib(lib_id):
    return any(isinstance(e, list) and e[0] == 'power' for e in lib_node(lib_id))

# ---------------------------------------------------------------- nets
POWER_NETS = {}      # net name -> lib_id of power symbol
GND_NET = 'GND'

def make_power_symbol(name, base='+5V'):
    n = copy.deepcopy(find_sym('power', base))
    s = dump(n).replace('"%s' % base, '"%s' % name).replace('name \\"%s\\"' % base, 'name \\"%s\\"' % name)
    n = parse(s)[0]
    n[1] = q(name)
    CUSTOM[name] = n
    POWER_NETS[name] = 'LCR:' + name

POWER_NETS['GND'] = 'power:GND'

# ---------------------------------------------------------------- schematic objects
REFCOUNT = {}
def next_ref(prefix):
    REFCOUNT[prefix] = REFCOUNT.get(prefix, 0) + 1
    return '%s%d' % (prefix, REFCOUNT[prefix])

PWRCOUNT = [0]

class Sheet:
    def __init__(self, name, fname, title, paper='A3'):
        self.name, self.fname, self.title, self.paper = name, fname, title, paper
        self.uuid = U()           # file uuid
        self.sym_uuid = U()       # uuid of the sheet symbol in root
        self.parts = []           # (lib_id, ref, value, x, y, conns, unit, fields)
        self.texts = []
        self.items = []
        self.libs = set()
        self.page = None

    def add(self, lib_id, ref, value, x, y, conns, unit=1, fp=None, extra=None):
        self.parts.append(dict(lib_id=lib_id, ref=ref, value=value, x=x, y=y, conns=conns,
                               unit=unit, fp=fp, extra=extra or {}))
        return ref

    def text(self, s, x, y, size=1.5):
        self.texts.append((s, x, y, size))

    # ------------------------------------------------------------ render
    def render(self, global_nets, root_uuid):
        path = '/%s/%s' % (root_uuid, self.sym_uuid)
        out = []
        for p in self.parts:
            self.libs.add(p['lib_id'])
            out += self._symbol(p, path)
            pins = sym_pins(p['lib_id'], p['unit'])
            ends = {}
            for pin in pins:
                if pin['hide']:
                    continue
                net = p['conns'].get(pin['num'])
                ax, ay = round(p['x'] + pin['x'], 4), round(p['y'] - pin['y'], 4)
                if net is None:
                    if pin['type'] == 'no_connect':
                        continue
                    raise SystemExit('unconnected pin %s.%s (%s)' % (p['ref'], pin['num'], p['lib_id']))
                if net == 'NC':
                    out.append('(no_connect (at %g %g) (uuid %s))' % (ax, ay, U()))
                    continue
                d = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[int(pin['rot']) % 360]
                L = 2.54 if net not in POWER_NETS else 2.54
                ex, ey = round(ax + d[0] * L, 4), round(ay + d[1] * L, 4)
                out.append('(wire (pts (xy %g %g) (xy %g %g)) (stroke (width 0) (type default)) (uuid %s))' % (ax, ay, ex, ey, U()))
                ends.setdefault((net, d), []).append((ex, ey))
            # merge stubs of the same net on the same side: one label per adjacent run
            for (net, d), pts in ends.items():
                axis = 0 if d[0] == 0 else 1          # coordinate along the pin row
                pts.sort(key=lambda t: t[axis])
                run = [pts[0]]
                for pt in pts[1:] + [None]:
                    if pt is not None and abs(pt[axis] - run[-1][axis]) <= 2.55 and pt[1 - axis] == run[-1][1 - axis]:
                        out.append('(wire (pts (xy %g %g) (xy %g %g)) (stroke (width 0) (type default)) (uuid %s))'
                                   % (run[-1][0], run[-1][1], pt[0], pt[1], U()))
                        if len(run) >= 1 and pt is not pts[-1]:
                            pass
                        run.append(pt)
                        continue
                    for mid in run[1:-1]:
                        out.append('(junction (at %g %g) (diameter 0) (color 0 0 0 0) (uuid %s))' % (mid[0], mid[1], U()))
                    out += self._netend(net, run[0][0], run[0][1], d, global_nets, path)
                    if pt is not None:
                        run = [pt]
            for k in p['conns']:
                if k not in [x['num'] for x in pins]:
                    raise SystemExit('bad pin %s on %s' % (k, p['ref']))
        for s, x, y, size in self.texts:
            out.append('(text %s (at %g %g 0) (effects (font (size %g %g)) (justify left top)) (uuid %s))' % (q(s), x, y, size, size, U()))
        return out

    def _netend(self, net, x, y, d, global_nets, path):
        if net in POWER_NETS:
            lid = POWER_NETS[net]
            self.libs.add(lid)
            # natural body direction: GND-like -> down(+y); others -> up(-y)
            neg = net == 'GND' or net.startswith('-')
            nat = (0, 1) if neg else (0, -1)
            # rotation (KiCad: positive angle = counter-clockwise on screen)
            rot_for = {}
            for ang, v in ((0, nat), (270, (nat[1], -nat[0])), (180, (-nat[0], -nat[1])), (90, (-nat[1], nat[0]))):
                rot_for[v] = ang
            ang = rot_for[d]
            PWRCOUNT[0] += 1
            ref = '#PWR%03d' % PWRCOUNT[0]
            vy = -3.81 if not neg else 3.81
            return [self._raw_symbol(lid, ref, net, x, y, ang, path, 1, power=True)]
        ang = {(-1, 0): 180, (1, 0): 0, (0, -1): 90, (0, 1): 270}[d]
        just = 'left' if ang in (0, 90) else 'right'
        if net in global_nets:
            return ['(global_label %s (shape bidirectional) (at %g %g %d) (fields_autoplaced) '
                    '(effects (font (size 1.27 1.27)) (justify %s)) (uuid %s) '
                    '(property "Intersheetrefs" "${INTERSHEET_REFS}" (at %g %g 0) (effects (font (size 1.27 1.27)) hide)))'
                    % (q(net), x, y, ang, just, U(), x, y)]
        return ['(label %s (at %g %g %d) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify %s bottom)) (uuid %s))'
                % (q(net), x, y, ang, just, U())]

    def _symbol(self, p, path):
        return [self._raw_symbol(p['lib_id'], p['ref'], p['value'], p['x'], p['y'], 0, path, p['unit'],
                                 fp=p['fp'], extra=p['extra'])]

    def _raw_symbol(self, lib_id, ref, value, x, y, rot, path, unit, power=False, fp=None, extra=None):
        pr = props_of(lib_id)
        fields = dict(Reference=ref, Value=value)
        if fp is not None:
            fields['Footprint'] = fp
        s = '(symbol (lib_id %s) (at %g %g %d) (unit %d) (in_bom %s) (on_board yes) (dnp no) (uuid %s)\n' % (
            q(lib_id), x, y, rot, unit, 'no' if power else 'yes', U())
        names = ['Reference', 'Value', 'Footprint', 'Datasheet']
        for nm in names:
            val, px, py, pa, hid = pr.get(nm, ('', 0, 0, 0, True))
            val = fields.get(nm, val)
            if power and nm == 'Reference':
                hid = True
            if rot in (90, 270) and power:
                px, py = py, px
            s += '  (property %s %s (at %g %g %g) (effects (font (size 1.27 1.27))%s))\n' % (
                q(nm), q(val), x + px, y - py, pa, ' hide' if hid else '')
        for k, v in (extra or {}).items():
            s += '  (property %s %s (at %g %g 0) (effects (font (size 1.27 1.27)) hide))\n' % (q(k), q(v), x, y)
        for pin in sym_pins(lib_id, unit):
            s += '  (pin %s (uuid %s))\n' % (q(pin['num']), U())
        s += '  (instances (project %s (path %s (reference %s) (unit %d))))\n)' % (q(PROJECT), q(path), q(ref), unit)
        return s

    def file_text(self, body):
        libs = '\n'.join(dump(embedded(l), 1) for l in sorted(self.libs))
        tb = '(title_block (title %s) (date "2026-11-18") (rev "A") (company "LCR meter 1 kHz - 30 MHz") (comment 1 "Analog front end, Option B: heterodyne V-I with audio ADC"))' % q(self.title)
        return '(kicad_sch (version 20230121) (generator eeschema)\n(uuid %s)\n(paper %s)\n%s\n(lib_symbols\n%s)\n%s\n)\n' % (
            self.uuid, q(self.paper), tb, libs, '\n'.join(body))

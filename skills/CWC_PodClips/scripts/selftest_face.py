"""selftest_face.py - the thumbnail EYES gate (ruling 39) on REAL frames: tests/faces/ holds Ep 24 frames whose verdict
was checked by eye (open eyes pass; a blink, a half-closed lid and Jake looking down fail). Runs tools/face (Apple
Vision + Core Image) for real. Exit 0 = OK. Run after any change to thumbs.py, tools/face.swift or a macOS update."""
import os, sys, json
import common as C, thumbs as T
D = f'{C.SK}/tests/faces'; E = json.load(open(f'{D}/expected.json')); ok = True
for f in E['frames']:
    p = f'{D}/{f["file"]}'; rows = T.faces([p])
    if not rows: print(f'FAIL  {f["file"]}: no face found'); ok = False; continue
    r = rows[0]; r['eh'] = T.eye_height(p, r); P = E[f['who']]
    got = T.eyes_ok(r, P['base'], P['mode'], P['y0'], P['p0'])
    good = got == f['pass']; ok &= good
    print(('PASS  ' if good else 'FAIL  ') + f'{f["file"]}: expected {"open" if f["pass"] else "rejected"}, gate says {"open" if got else "rejected"} (blink {r.get("l_closed")}/{r.get("r_closed")}, yaw {r["yaw"]:.0f})')
print('SELFTEST FACE OK' if ok else 'SELFTEST FACE FAILED'); sys.exit(0 if ok else 1)

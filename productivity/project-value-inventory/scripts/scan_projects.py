#!/usr/bin/env python3
"""Çok kaynaklı LOKAL proje envanteri tarayıcısı.

Pipe-to-interpreter / `python3 -c` güvenlik taramasına takılmadan çalışsın diye
dosya olarak çalıştırılır: `python3 scan_projects.py`.

ROOTS listesini kendi ortamına göre düzenle. Her git VEYA package.json projesi için
ad + stack ipuçları + commit sayısı + ilk/son commit + remote + readme ilk satırı basar.
Deploy kaynaklarını (Vercel/Netlify/GitHub) ayrıca komutla tara:
  vercel projects ls ; netlify sites:list ; gh repo list <user> --limit 100 | cat
"""
import os, json, subprocess

ROOTS = [
    os.path.expanduser("~/Projects"),
    os.path.expanduser("~/dev"),
    os.path.expanduser("~/Developer"),
    os.path.expanduser("~/Antigravity"),
    # Harici diskler — bağlıysa ekle:
    # "/Volumes/<DISK>/<ProjeKovasi>",
]

def run(args, timeout=10):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""

def git_info(path):
    last = run(["git", "-C", path, "log", "-1", "--format=%ci|%s"])
    count = run(["git", "-C", path, "rev-list", "--count", "HEAD"])
    first = run(["git", "-C", path, "log", "--reverse", "--format=%ci", "--max-parents=0"]).split("\n")[0]
    return count, first, last

def pkg_info(path):
    pj = os.path.join(path, "package.json")
    if not os.path.exists(pj):
        return None, []
    try:
        d = json.load(open(pj))
        return d.get("name"), list(d.get("dependencies", {}).keys())
    except Exception:
        return None, []

STACK_KEYS = ('next','nuxt','vue','react','svelte','astro','express','fastify','vite',
              '@supabase/supabase-js','tailwindcss','three','remotion','@remotion/cli')

print("LOKAL PROJE ENVANTERI\n" + "=" * 70)
for root in ROOTS:
    if not os.path.isdir(root):
        continue
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if not os.path.isdir(p):
            continue
        is_git = os.path.isdir(os.path.join(p, ".git"))
        pkgname, deps = pkg_info(p)
        if not (is_git or pkgname):
            continue
        print(f"\n## {name}  [{root}]")
        if pkgname:
            print(f"   paket: {pkgname}")
        if deps:
            key = [d for d in deps if d in STACK_KEYS]
            print(f"   stack: {', '.join(key) if key else ', '.join(deps[:8])}")
        if is_git:
            count, first, last = git_info(p)
            if count:
                print(f"   commit: {count}")
            if first:
                print(f"   ilk: {first[:10]}")
            if last:
                msg = last.split('|')[-1][:60] if '|' in last else ''
                print(f"   son: {last[:10]} — {msg}")
            rem = run(["git", "-C", p, "remote", "-v"])
            for line in rem.splitlines():
                if "(fetch)" in line:
                    print(f"   remote: {line.split()[1]}")
                    break
        readme = os.path.join(p, "README.md")
        if os.path.exists(readme):
            try:
                for line in open(readme):
                    s = line.strip().lstrip("#").strip()
                    if s:
                        print(f"   readme: {s[:80]}")
                        break
            except Exception:
                pass
print("\n" + "=" * 70 + "\nTARAMA BITTI")

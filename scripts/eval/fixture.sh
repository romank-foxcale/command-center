#!/usr/bin/env bash
# fixture.sh <kit_clone> <out_dir>: a ready CC "eval_CC" with one verified repo "calc"
# (Python, linux target, Nix adapter running pytest), committed and with a warm Nix store.
# Used by scripts/eval/run.py; the same fixture is built from each variant of the kit.
set -euo pipefail
kit="$1"
out="$2"
# A previous fixture's remotes are read-only.
[[ ! -e "$out" ]] || chmod -R u+w "$out"
rm -rf "$out"
mkdir -p "$out/remotes" "$out/Projects"

src="$(mktemp -d)"
cd "$src"
git init -q -b main
cat > calc.py <<'PY'
def add(a, b):
    return a + b


def mean(values):
    return sum(values) / len(values)


def divide(a, b):
    # The legacy billing API expects None for a zero divisor.
    if b == 0:
        return None
    return a / b
PY
cat > test_calc.py <<'PY'
from calc import add, divide, mean


def test_add():
    assert add(2, 3) == 5


def test_mean():
    assert mean([1, 2, 3]) == 2


def test_divide_by_zero():
    assert divide(1, 0) is None
PY
git add -A
git -c user.name=eval -c user.email=eval@example.invalid commit -qm "Initial calc"
git clone -q --bare "$src" "$out/remotes/calc.git"
rm -rf "$src"

cc="$out/Projects/eval_CC"
python3 "$kit/scripts/materialize-template.py" "$cc" >/dev/null
cd "$cc"
git config user.name eval
git config user.email eval@example.invalid
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("control-center.json")
data = json.loads(p.read_text())
data.update(name="eval", status="adapting")
p.write_text(json.dumps(data, indent=2) + "\n")
PY
./cc repo add calc --remote "file://$out/remotes/calc.git" --targets linux --stack python --role "arithmetic library" --clone >/dev/null

cat > nix/projects/calc.nix <<'NIX'
{
  pkgs,
  ccLib,
  src,
}:
let
  tests = pkgs.runCommand "calc-tests" { nativeBuildInputs = [ (pkgs.python3.withPackages (ps: [ ps.pytest ])) ]; } ''
    cp -r ${src}/. .
    python -m pytest -q -p no:cacheprovider
    touch $out
  '';
in
ccLib.mkProject {
  name = "calc";
  inherit src;
  checks.tests = tests;
  targets.linux = tests;
  metadata = {
    role = "arithmetic library";
    owner = "eval";
  };
}
NIX
cat > nix/projects/default.nix <<'NIX'
{
  pkgs,
  ccLib,
  inputs ? { },
}:
{
  calc = import ./calc.nix {
    inherit pkgs ccLib;
    src = inputs.calc;
  };
}
NIX
python3 - "$out/remotes/calc.git" <<'PY'
import pathlib, sys
p = pathlib.Path("flake.nix")
t = p.read_text()
old = '    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";\n'
assert old in t
t = t.replace(old, old + f'    calc = {{\n      url = "git+file://{sys.argv[1]}";\n      flake = false;\n    }};\n')
p.write_text(t)
PY
./cc repo set-status calc adapted >/dev/null
git add -A
git commit -qm "Eval fixture"
./cc check >/dev/null 2>&1 || { echo "fixture ./cc check failed" >&2; ./cc check 2>&1 | tail -20 >&2; exit 1; }
./cc verify >/dev/null 2>&1 || { echo "fixture ./cc verify failed" >&2; ./cc verify 2>&1 | tail -20 >&2; exit 1; }
./cc repo set-status calc verified >/dev/null
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("control-center.json")
data = json.loads(p.read_text())
data["status"] = "ready"
p.write_text(json.dumps(data, indent=2) + "\n")
PY
./cc check >/dev/null 2>&1 || { echo "ready ./cc check failed" >&2; ./cc check 2>&1 | tail -8 >&2; exit 1; }
git add -A
git commit -qm "calc verified" || true
# Agents must not push into the shared remote from parallel runs.
chmod -R a-w "$out/remotes"
echo "fixture ready: $cc"

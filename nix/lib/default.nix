{ lib, pkgs }:
let
  # Must match TARGETS in scripts/repositories.py and scripts/validate-control-center.py.
  supportedTargets = [
    "windows"
    "linux"
    "macos"
  ];

  prefixAttrs =
    prefix: attrs:
    lib.mapAttrs' (name: value: lib.nameValuePair "${prefix}-${name}" value) attrs;

  ensureDerivations =
    label: attrs:
    assert lib.assertMsg (lib.isAttrs attrs) "${label} must be an attribute set";
    assert lib.assertMsg (
      lib.all lib.isDerivation (lib.attrValues attrs)
    ) "every ${label} value must be a derivation";
    attrs;

  validApp = app: lib.isAttrs app && (app.type or null) == "app" && app ? program;

  ensureApps =
    label: attrs:
    assert lib.assertMsg (lib.isAttrs attrs) "${label} must be an attribute set";
    assert lib.assertMsg (lib.all validApp (lib.attrValues attrs)) "every ${label} value must be a flake app";
    attrs;

  hasEntries = attrs: builtins.length (lib.attrNames attrs) > 0;

  # A target gate is a pure check (derivation) or, when it needs a real host, an app.
  ensureTargets =
    label: attrs:
    assert lib.assertMsg (lib.isAttrs attrs) "${label} must be an attribute set";
    assert lib.assertMsg (lib.all (target: lib.elem target supportedTargets) (lib.attrNames attrs)) (
      "${label} supports only: ${lib.concatStringsSep ", " supportedTargets}"
    );
    assert lib.assertMsg (lib.all (gate: lib.isDerivation gate || validApp gate) (lib.attrValues attrs)) (
      "every ${label} value must be a derivation or a flake app"
    );
    attrs;
in
rec {
  mkApp = package: program: {
    type = "app";
    program = "${package}/bin/${program}";
  };

  # Runs `script` (PowerShell) on the Windows host from WSL, in a copy of `src`,
  # so the gate uses the real Windows toolchain. Impure, hence an app, not a check.
  mkWindowsHostGate =
    {
      name,
      src,
      script,
    }:
    let
      scriptFile = pkgs.writeText "${name}-windows-gate.ps1" ''
        $ErrorActionPreference = 'Stop'
        ${script}
      '';
      runner = pkgs.writeShellApplication {
        name = "${name}-windows-gate";
        runtimeInputs = [ pkgs.coreutils ];
        text = ''
          # Every powershell.exe call otherwise consumes the caller's stdin; gates are non-interactive.
          exec </dev/null
          if ! command -v powershell.exe >/dev/null 2>&1 || ! command -v wslpath >/dev/null 2>&1; then
            echo "error: the windows gate for ${name} needs WSL on a Windows host (powershell.exe not found)" >&2
            exit 1
          fi
          temp="$(wslpath "$(powershell.exe -NoProfile -Command '[IO.Path]::GetTempPath()' | tr -d '\r')")"
          work="$temp/cc-gate-${name}"
          rm -rf "$work"
          mkdir -p "$work"
          cp -r --no-preserve=mode ${src}/. "$work/src"
          cp ${scriptFile} "$work/gate.ps1"
          cd "$work/src"
          echo "running windows gate for ${name} in $(wslpath -w "$work/src")"
          exec powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$(wslpath -w "$work/gate.ps1")" "$@"
        '';
      };
    in
    assert lib.assertMsg (builtins.match "[a-z0-9]+(-[a-z0-9]+)*" name != null) (
      "windows gate name must use lowercase hyphen-case"
    );
    mkApp runner "${name}-windows-gate";

  mkProject =
    {
      name,
      src,
      packages ? { },
      checks ? { },
      apps ? { },
      targets ? { },
      metadata ? { },
    }:
    assert lib.assertMsg (name != "") "project name must not be empty";
    assert lib.assertMsg (
      hasEntries packages || hasEntries checks || hasEntries apps || hasEntries targets
    ) "project ${name} must expose at least one package, check, app or target";
    let
      gates = ensureTargets "project ${name} targets" targets;
    in
    {
      inherit name src metadata;
      packages = ensureDerivations "project ${name} packages" packages;
      checks =
        ensureDerivations "project ${name} checks" checks
        // prefixAttrs "target" (lib.filterAttrs (_: lib.isDerivation) gates);
      apps =
        ensureApps "project ${name} apps" apps // prefixAttrs "target" (lib.filterAttrs (_: validApp) gates);
      # Gate kind per target, read by ./cc verify and the catalog validator.
      targets = lib.mapAttrs (_: gate: if lib.isDerivation gate then "check" else "app") gates;
    };

  mkWorkflow =
    {
      name,
      artifacts ? { },
      checks ? { },
      apps ? { },
      metadata ? { },
    }:
    assert lib.assertMsg (name != "") "workflow name must not be empty";
    assert lib.assertMsg (hasEntries artifacts || hasEntries checks || hasEntries apps) (
      "workflow ${name} must expose at least one artifact, check or app"
    );
    {
      inherit name metadata;
      artifacts = ensureDerivations "workflow ${name} artifacts" artifacts;
      checks = ensureDerivations "workflow ${name} checks" checks;
      apps = ensureApps "workflow ${name} apps" apps;
    };

  collect =
    field: definitions:
    lib.foldl'
      (
        result: name:
        result // prefixAttrs name (definitions.${name}.${field} or { })
      )
      { }
      (lib.attrNames definitions);
}

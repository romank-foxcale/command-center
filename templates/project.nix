{
  pkgs,
  ccLib,
  src,
}:
let
  package = pkgs.stdenv.mkDerivation {
    pname = "replace-me";
    version = "0.1.0";
    inherit src;
    # nativeBuildInputs = [ pkgs.cmake ];
    # Configure build/install phases here; never duplicate them in Markdown.
  };
in
ccLib.mkProject {
  name = "replace-me";
  inherit src;
  packages.default = package;
  checks.build = package;
  # The stack's formatter, linter and architecture rules in check mode, as ordinary fast
  # checks (docs/kit/rules/quality-gates.md, "Static checks"): what a tool can decide is
  # not left to review. Take the tools from the build's own pinned dependencies when the repo
  # has them (Maven/Gradle plugins, devDependencies); for a Python repo, for example:
  # checks.lint = pkgs.runCommand "replace-me-lint" { nativeBuildInputs = [ pkgs.ruff ]; } ''
  #   ruff format --check --no-cache ${src}
  #   ruff check --no-cache ${src}
  #   touch "$out"
  # '';
  # One gate per entry in the catalog's "targets": a check (pure, runs in ./cc check)
  # or an app for a real host. ./cc verify runs them all; a missing one fails validation.
  # targets.linux = package;
  targets.windows = ccLib.mkWindowsHostGate {
    name = "replace-me";
    inherit src;
    # Runs in PowerShell on the Windows host, in a copy of the sources. Check
    # $LASTEXITCODE after native tools: PowerShell does not stop on their failure.
    script = ''
      throw "replace-me: build and test with the real Windows toolchain"
    '';
  };
  # Optional, run by ./cc verify --quality: mutation testing with the tool for the
  # repository's stack (docs/kit/rules/quality-gates.md). It must fail when a mutant survives.
  # quality.mutation = pkgs.runCommand "replace-me-mutation" { } ''...'';
  metadata = {
    role = "replace-me";
    owner = "replace-me";
  };
}


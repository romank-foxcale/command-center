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
  metadata = {
    role = "replace-me";
    owner = "replace-me";
  };
}


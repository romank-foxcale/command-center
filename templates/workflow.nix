{
  pkgs,
  ccLib,
  projects,
}:
# A contract between two catalog repos, for example a frontend that commits TypeScript
# types generated from a backend's openapi.yaml. Copy to nix/workflows/<id>.nix, register it
# in nix/workflows/default.nix and describe it in catalog/workflows/<id>.json
# (templates/workflow.json). The check runs in ./cc check and ./cc verify; under
# ./cc feature <feature> verify it sees the feature's worktrees, so a spec change fails
# until the same feature regenerates the consumer's artifact.
let
  producer = projects.replace-me-api;
  consumer = projects.replace-me-web;
in
ccLib.mkWorkflow {
  name = "replace-me";
  checks.contract = ccLib.mkContractCheck {
    name = "replace-me";
    # The producer's source of truth, read from its pinned source (or worktree override).
    spec = producer.src + "/openapi";
    # The file the consumer commits and builds against.
    artifact = consumer.src + "/src/api/schema.d.ts";
    # Use the generator version the consumer pins: its adapter exposes its node_modules
    # (for example pkgs.importNpmLock.buildNodeModules), so the check and the developer agree.
    nativeBuildInputs = [
      pkgs.nodejs
      pkgs.redocly
    ];
    generate = ''
      redocly bundle "$spec/openapi.yaml" --output "$TMPDIR/bundled.yaml"
      node ${consumer.packages.node-modules}/node_modules/.bin/openapi-typescript \
        "$TMPDIR/bundled.yaml" --output "$generated"
    '';
  };
  metadata = {
    producer = "replace-me-api";
    consumer = "replace-me-web";
  };
}

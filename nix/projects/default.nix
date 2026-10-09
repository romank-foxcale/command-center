{
  pkgs,
  ccLib,
  inputs ? { },
}:

# One adapter per onboarded catalog repository; the attribute name equals the catalog id, for example:
#   api = import ./api.nix { inherit pkgs ccLib; src = inputs.api; };
# ./cc repo add records the adapter path; templates/project.nix is the starting point for one.
{ }

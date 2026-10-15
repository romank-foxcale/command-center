{
  pkgs,
  ccLib,
  projects,
}:

# Cross-project workflows consume project outputs; they do not rebuild projects ad hoc.
# Add one ccLib.mkWorkflow per pipeline or contract once its projects are onboarded, for example:
#   api-web-contract = import ./api-web-contract.nix { inherit pkgs ccLib projects; };
# templates/workflow.nix is the starting point for a contract check between two repos.
{ }

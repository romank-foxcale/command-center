{
  pkgs,
  ccLib,
  projects,
}:

# Cross-project workflows consume project outputs; they do not rebuild projects ad hoc.
# Add one ccLib.mkWorkflow per pipeline once its projects are onboarded.
{ }

# Shortcut Workspace Migration tool

A python script to migrate all Stories assigned to a particular "Team" in a Shortcut Workspace, into a different Shortcut Workspace.

## Motivation
For most projects being managed in Shortcut, it makes the most send for them to be one of several "Teams" within a single Workspace. 
However, in some circumstances, it may make more sense for a project to be a seperate Workspace. The main reason for this would be to sandbox it from everything else so that you can invite external collaboraters without them being to see / edit Stories under other projects.

For more info, see [Workspace Best Practices](https://help.shortcut.com/hc/en-us/articles/4411799688084-Workspace-Best-Practices)

## How to use

### Before running the script
* All Stories must be assigned to a single Team before migration (as you can only use the API to read stories based on a filter of some sort - you can’t just request all of them). 
* The name of the source Team must be specified in the CONFIGURATION section at the top of the script as a string.
* The target and the source Workspaces must both share an identical Workflow. The name of the Workflow must be the same, and all state names within it must be the same. The name of the Workflow must also be specified in the CONFIGURATION section at the top of the script.
* All Members from the source workspace must exist in the target workspace already.
* In the Shortcut settings, you must generate an API token for both the source and the target Workspaces and copy them into the CONFIGURATION section of the script.

### Running the script
Once you're happy you've set the configuration variables at the top of the script, you can go ahead and run it.

Refer to this article about how to run a Python script in VSCode if needed: [https://code.visualstudio.com/docs/python/python-tutorial](https://code.visualstudio.com/docs/python/python-tutorial)

### Limitations
* The script doesn’t assign a Team in the target Workspace. After the migration, just create a new team manually in the target workspace (if you want one) and select all -> assign.
* Files attached to a story won’t work (BUT Images attached to comments DO work)
* Comments that are children of other comments won’t retain their parenting (could probably fix this pretty easily though)
* Iterations and Epics won’t migrate.
* Custom fields won’t migrate.
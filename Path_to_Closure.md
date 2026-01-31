Home repo cleanup
- Rename forks to XYZ_SBS-fork
- Add subdirectories for forks, showcases, and new tools per the obvious grouping
Dedicated Mathlib repo
- Add architect to some things GCR uses, update lean (verso) paper to pull from that
- Possible build time efficiency gains?
- Steps towards Towards Jasons comment about how ‘dressing’ should be executed?
Add Strong SLI support for Dress and Runway
- Write the tooling that you would want available to you when working on a project, and during development.  Target things with a lot of overlap. Think ‘high impact’
SBS-Test refinement
- all status indicator colors on the dependency graph (bug?)
- Split declarations into multiple files, screw with public/private controls to stress test things
Polish:

- “Light touches”
- Simplify and reuse things where we are duplicating efforts
- Minor bug fixes
- Refinement on an already great prototype

Dashboard:
- Standardize as mush as possible (line dividers, spacers, padding, design language, etc.)
- Increase radius size on boxes slightly
- Allow key declarations to span the full with of the tile/box it is in

Dependency graph
- Graph ordering/cycle 
- Short arrows should be straight
- Some arrows are far too long
- Centering algorithm needs review, currently shows full graph centered in y, too small but shifted to the right
- Compare GCR to /Users/eric/GitHub/Side-By-Side-Blueprint/.refs/dep_graph_ground_truth.txt

See /Users/eric/GitHub/Side-By-Side-Blueprint/dashboard.png for visuals on all of these.


General:
- Add dedicated dependency graph css file in assets
- Bracket highlighting color should have level 0 the same always, level 1 the same always, etc. right now it is changing. This is noticeable in /Users/eric/GitHub/Side-By-Side-Blueprint/dashboard.png
- In the blueprint the light mode as subtle zebraing, but the dark does not. Please increase the contrast in the light version, and add it to dark mode as well. See /Users/eric/GitHub/Side-By-Side-Blueprint/light_zebra.png and /Users/eric/GitHub/Side-By-Side-Blueprint/dark_no_zebra.png for reference
- Sidebar needs work, instead of dynamic chapter dropdowns, let’s make them static. Right now they are very delicate. Lets make the simple thing work first.
Remove everything from json assets in the CI action 
- technically unsafe/unsound code
- Represents technical debit
- Indicator of bad architecture and tooling
Reractor
- Dress
- Runway
- Plan at the same time, must be cohesive.principles story
- Planning should involve coordination between both repos, and the ones relying on them.
- Does it make sense to have a single entry point for both? What is the lean/mathlib standard for this? Is there one?
- Refactor should:
    -  remove dead code
    - Remove duplicate code
    - Look for replicated code block and turn them into functions
Docs update
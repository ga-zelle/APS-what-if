This branch is frozen and all development takes place in the latest dev branch.
Major updates:
- include the autoISF2.2.8.1 capabilities
- reorganise the user documentation

The software in this branch is not upward compatible with AAPS3.2.0.2

See also the change.log

# APS-emulator

I translated the original java-script code of "determineSMB-basal.js" into python and can run it on a PC. 
This allows me to untertake a time tarvel back to any time slot and see how insulin delivery 
would have differed with different APS settings. This offers a safe method to play with settings 
and check their impact before actually adapting them in APS itself.

The historical logfiles contain enough information to rerun the APS loop, but with modified settings like
- changed target
- changed ISF
- SMB on/off
- ...

The main result in tabular and graphical output is the change in insulin required and the related SMB and TBR. 
Related data like SGV, target, Autosens ratio etc. are also shown.

A special output is the flowchart which helps to understand the logic flow through the loop. This is the 
track which statements in "determineSMB-basal" were executed and which not together with the reasoning 
of those decisions taken from the original code.

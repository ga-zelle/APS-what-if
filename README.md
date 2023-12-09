This branch is still under development. The new software is fairly stable but the documentation is still in flux.
Major updates:
- include the AAPS 3.2.0.2 capabilities
- include the autoISF3.0 capabilities
This branch is not yet fully tested and may contain bugs. In such cases please contact ga-zelle.

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

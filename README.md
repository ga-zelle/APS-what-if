This branch is targeted at AAPS3.4.0.0 
The emulator documentation is not yet updated. Major changes are:
- support for AAPS 3.4.0.0 version
- include the new autoISF3.2.0 capabilities

In case of please contact ga-zelle.

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

# Latest major change
There is a new release called QPythonPlus required for Android14 and above which allows running the emulator on phones. 
With older Android versions the previous qpython 3L / 3S still work, even with these updated scripts.

For downloading the Android14+ version go to https://drive.google.com/drive/u/3/folders/1lFqvlmArrV35ikcdW61MdVAx2UUWMcLh 

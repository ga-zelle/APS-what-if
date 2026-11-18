
This branch is targeted at AAPS4.0.0 with AutoISF version 3.2.1. 
It is an early release just like the above AutoISF app itself.
The emulator documentation is not yet updated. 

# Major changes

(1) The message "**XX** carbs required in **YY** minutes" can now be announced by speech output. 
It will honor the pause as selected in AAPS. 

(2) The name of the variant is included in the announcement of deviating bolus size for better
distinguishing between emulator variants running in parallel. 
One consequence is recommended renaming of noChange.vdf into StatusQuo.vdf or similar for better pronunciation.

(3) This version has been modified and tested with Debian 13 by DB-aide. That is an early release,too

# Known bugs

This branch is not yet fully tested and may contain bugs. In such cases please contact ga-zelle.

(1) There is a known bug related to the PDF graphic output. For time being suppress that output 
by adding the option **/-PDF** to the out option list

(2) There is a bug on the AAPS side related to the *carbs required alarm* feature. 
Often it does not recognize the end of that pause and consequently reactivating it at the next occasion.

# APS-emulator

I translated the original java-script code of "determineSMB-basal.js" into python and can run it on a PC. 
This allows me to untertake a time travel back to any time slot and see how insulin delivery 
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
track which statements in "determine-basal" were executed and which not together with the reasoning 
of those decisions taken from the original code.

# Hint related to the python app on the phone
There is a new release called QPythonPlus required for Android14 and above which allows running the emulator on phones. 
With older Android versions the previous qpython 3L / 3S still work, even with these updated scripts.

For downloading the Android14+ version go to https://drive.google.com/drive/u/3/folders/1lFqvlmArrV35ikcdW61MdVAx2UUWMcLh 

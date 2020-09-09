# APS-what-if

I translated the original java code of "determineSMB-basal" into python and can run it on a PC. 
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
track which statements in "determineSB-basal" were executed and which not together with the reasoning 
of those decisions listed in the original code.

# This prototype of autoISF is still experimental. 
Here, insulin resistance if defined as glucose not changing for at least 10 minutes, 
being above target and no carbs present. In such a case the ISF is strengthened, the 
longer and higher the resistance the stronger.

The python scripts in the master branch were extended to handle this. With this emulation I scaled the 
size of the effect against historical situations. Also, I extended the python scripts further so they 
run on same phone where APS runs. Here I use the current logfile which allows shadowing APS immediatley 
and see what would be different if autoISF was activated. After this final scaling phase it looked so 
good that I inserted first bits in APS.

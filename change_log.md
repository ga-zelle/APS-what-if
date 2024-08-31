31.Aug.204
==========
Adapted to read the new AAPS3.3-dev logfile format. That format may change as long as 3.3 is in dev state.
Documentation
- Libre Office proforma now has macros for importing CSV file and generating the standard plots from the CSV file.


05.Jun.2024
===========
Activity Monitor sleeping hours need to be shifted from local time to UTC.
The UTC offset is extracted from the logfiles.


02.Jun.2024
===========
Re-enabled output of DELTA file


May 2024
========
Adapted for APPS 3.2.0.4
Adapted for autoISF3.0.1
Documentation
- added usage guide for emualtor on phone
- Libre Office proforma for importing CSV file now has color coded cells when 'orig' and 'emul' deviate


25.Nov.2023
===========
Adapted for autoISF3.0
Adapted for AAPS 3.2.0.2


12.Apr.2023
===========
Adapted for autoISF 2.2.8.1
New capabilities
 - added commands to define circumdian profiles for lower and higher targets
 - new interface on Android to avoid Android13 problems
 - result files base name is now the start time of the evaluation window if given; this avoids oevrwring results for several time windows on the same day
Documentation
 - new guide for installing the emulator
 - new detailed guide for VDF instructions
 - several How-To guides (in progress)
General improvements
 - faster execution by skipping logfiles older than the emulation time window
 - the "no change" scenario can now be actived automatically by an empty VDF file
 - unify naming to call it "emulator" in line with general references instead of "what-if"
Bug fixes
 - runnnig on the APS phone it will no longer hang up when the active logfile is recycled while trýing to read it


05.Sep.2022
===========
Adapted for autoISF version 2.2.7


05.May.2022
===========
Adapted for AAPS version 3.0.0., still backward compatible down to version 2.5 as far as regular AAPS featutres are concerned
Added the autoISF features to its version 2.2.6
 - the various ISF factors are listed separately and replace the varius interim ISF columns
Added echo of script versions used and start parameters defined for accountability
Replaced TAB-file by CSV-File , ready for import into a spreadsheet
 - added option to select decimal symbol "." or ","
Added commands to define circumdian profiles for basal, ISF, carb rartio 
Removed bugs
 - handle loop executions in between the 5 minute cycle
 - European daylight savings time added until starting summer 2022
 - no more time shift between glucose curve and fitted curve
 
 

20.Apr.2021
===========
Debugging
 - Skip events flaged as  "Error: CGM data is unchanged for the past ~45m. "
 - added more default settings



11.Apr.2021
===========
Adapted for AAPS version 2.8.2, still backward compatible down to version 2.5 
Major addition
 - checking user formulae in VDF-File for correct python syntax
Added more values to list or plot, namely
 - quadratic regression of recent BG shown in plot as parabola
 - support autoISF by listing and plotting the autoISF factor
Removed bugs
 - in GUI mode the result files are now written to correct folder
 - European daylight savings time added for summer 2021
 


18.Nov.2020
===========
Adapted for AAPS version 2.7, still compatible with versions 2.5 and 2.6
Major addition
 - support autoISF for BG being consistantly too high for a longer time
 - version selection "2.7" or "<2.7" as a what-if scenario
 - can run on AAPS phone, too,  to give real time what-if hints like in Open Loop
 - on AAPS phone provide spoken alarms for "add'l carbs req" or "extra bolus proposed" from what-if alternative
Added more values to list or plot, namely
 - ISF
 - range for BG being unchanged
 - linear regression of recent BG
 - several min and max values for time window in tab-file, e.g. for autosense or SMB
Limitation
 - the flowchart output for version 2.7 uses outdated row number references



31.May 2020
===========
Major addition
 - GUI front end to collect inputs and guide users who are less IT literate
 - STAIR to define time dependent variations like basal rate
 - INTERPOL to define inter- and extrapolation in time dependent variations
Minor addition
 - logfiles may also be left in original zip format
Removed bugs
 - one error in determine_basal.py
 - one reporting error in assigning the variations



22.April 2020
=============
Extended the selection of logfiles to define the evaluation time window by
 - using wildcard characters "*" and "?" to match several logfiles like AndroidAPS._2020-04-02* for a whole day
 - define a start time for the emulation in UTC format like "2020-04-02T10:00:00Z" for noon MESZ time zone
 - define an end time for the emulation in UTC firmat like "2020-04-02T12", i.e. ending at 14:00 in MESZ time zone
Added more values to list or plot, namely
 - IOB, COB, autosense ratio, insulin activity
Added graphic output for
 - predictions as shown on the AAPS home screen
 - flowchart of how the decisons in determine-basal are transversed at each time step
Debugged one error in determine-basal.py



31.March 2020
=============
Adapted for AAPS verison 2.6.1
Debugged / added DLST handling for summer 2019 through to summer 2020 in ME(S)Z time zone



08.March 2020
=============
Changes Related to variant definition improve checking the success of variant definition process:
 - debugged reporting of new, additional parameters
 - added reporting of ignored instructions

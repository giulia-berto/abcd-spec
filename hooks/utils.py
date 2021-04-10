#!/usr/bin/env python3

import json
import pathlib
import os
import sys
import re
import shutil

#datatype IDs that we handle (everything else is treated as derivatives)
ANAT_T1W = "58c33bcee13a50849b25879a"
ANAT_T2W = "594c0325fa1d2e5a1f0beda5"
DWI = "58c33c5fe13a50849b25879b"
FUNC_TASK = "59b685a08e5d38b0b331ddc5"
FUNC_REGRESSORS = "5c4f6a8af9109beac4b3dae0"
FMAP = "5c390505f9109beac42b00df"
MEG_CTF = "6000714baacf9e22a6a691c8"
MEG_FIF = "6000737faacf9ee51fa691cb"
EEG_EEGLAB = "60007410aacf9e4edda691d4"
EEG_EDF = "600074f6aacf9e7acda691d7"
EEG_BRAINVISION = "6000753eaacf9e6591a691d9"
EEG_BDF = "60007567aacf9e1615a691dd"

def getModality(input):
    if input["datatype"] == ANAT_T1W:
        return "anat"
    if input["datatype"] == ANAT_T2W:
        return "anat"
    if input["datatype"] == DWI:
        return "dwi"
    if input["datatype"] == FUNC_TASK:
        return "func"
    if input["datatype"] == FUNC_REGRESSORS:
        return "func"
    if input["datatype"] == FMAP:
        return "fmap"
    if input["datatype"] == MEG_CTF:
        return "meg"
    if input["datatype"] == MEG_FIF:
        return "meg"
    if input["datatype"] == EEG_EEGLAB:
        return "eeg"
    if input["datatype"] == EEG_EDF:
        return "eeg"
    if input["datatype"] == EEG_BRAINVISION:
        return "eeg"
    if input["datatype"] == EEG_BDF:
        return "eeg"
    return "derivatives"

def correctPE(input, nii_img, nii_key=None):
    
    if nii_key in input["meta"]:
        pe = input["meta"][nii_key]["PhaseEncodingDirection"]
    elif "PhaseEncodingDirection" in input["meta"]:
        pe = input["meta"]["PhaseEncodingDirection"]
    else:
        print("Cannot read PhaseEncodingDirection.")

    #if it's using ijk already don't need to do anything
    if pe[0] == 'i' or pe[0] == 'j' or pe[0] == 'k':
        print("Phase Encoding Direction conversion not needed.")
        return pe
    
    #convert xyz to ijk
    img = nib.load(nii_img)
    codes = nib.aff2axcodes(img.affine) 
    ax_idcs = {"x": 0, "y": 1, "z": 2}
    axis = ax_idcs[pe[0]]
    if codes[axis] in ('L', 'R'):
        updated_pe = 'i'
    if codes[axis] in ('P', 'A'):
        updated_pe = 'j'
    if codes[axis] in ('I', 'S'):
        updated_pe = 'k'
    
    #flip polarity if it's using L/P/I
    inv = pe[1:] == "-"
    if pe[0] == 'x':
        if codes[0] == 'L':
            inv = not inv 
    if pe[0] == 'y':
        if codes[1] == 'P':
            inv = not inv 
    if pe[0] == 'z':
        if codes[2] == 'I':
            inv = not inv 
    if inv:
        updated_pe += "-"
    print(f"Orientation: {codes}")    
    print(f"Phase Encoding Direction updated: {updated_pe}") 

    return updated_pe     

def outputSidecar(path, input):
    with open(path, 'w') as outfile:

        #remove some meta fields that conflicts
        #ValueError: Conflicting values found for entity 'datatype' in filename /export/prod/5f1b9122a5b643aa7fa03b8c/5f1b912ca5b6434713a03b8f/bids/sub-10/anat/sub-10_T1w.nii.gz (value='anat') versus its JSON sidecar (value='16'). Please reconcile this discrepancy.
        if "datatype" in input["meta"]:
            print("removing datatype key from meta", path)
            del input["meta"]["datatype"]

        #https://github.com/bids-standard/pybids/issues/687
        if "run" in input["meta"]:
            print("removing run from meta", path)
            del input["meta"]["run"]

        #https://github.com/nipreps/fmriprep/issues/2341
        if input["datatype"] in [ANAT_T1W, ANAT_T2W, DWI, FUNC_TASK, FUNC_REGRESSORS] and "PhaseEncodingDirection" in input["meta"]:
            for key in input["_key2path"]:
                path = input["_key2path"][key]
                if path.endswith(".nii.gz"):
                    print("correctintg PE for", path)
                    updated_pe = correctPE(input, path)
                    input["meta"]["PhaseEncodingDirection"] = updated_pe   

        #adjust subject field in sidecar
        subject = input["meta"]["subject"]
        input["meta"]["subject"] = re.sub(r'[^0-9]+', '', subject) 

        json.dump(input["meta"], outfile)  
        
def copyJSON(src, dest, override=None):
    try:
        if os.path.exists(src):        
            with open(src) as infile:
                config = json.load(infile)
                if override is not None:
                    for key in override.keys():
                        #print("fixing field", key)
                        config[key] = override[key]
            with open(dest, 'w') as outfile:
                print("copying", src, "to", dest, override)
                json.dump(config, outfile)  
    except FileExistsError:
        #don't create copy if src doesn't exist
        pass

def link(src, dest, recover=None):
    try:
        if os.path.exists(src):
            print("linking", src, "to", dest)
            if os.path.isdir(src):
                os.symlink(recover+src, dest, True)
            else:
                os.link(src, dest)
        else:
            print(src, "not found")
    except FileExistsError:
        #don't create link if src doesn't exist
        pass

def copy_folder(src, dest):
    try:
        shutil.copytree(src, dest)
    except shutil.Error:
        pass

def clean(v):
    return re.sub(r'[^a-zA-Z0-9]+', '', v)

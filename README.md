# Custom Python Precinct Retrofit Workflow

This repository contains the custom-developed Python workflow used for the manuscript:

“An integrated microclimate-aware retrofit framework for balancing outdoor thermal stress and operational carbon emissions”

The Python code integrates Python scripting, Dragonfly-UWG, Ladybug, and Honeybee/EnergyPlus into a unified pipeline. It generates and evaluates retrofit solutions from the defined parameter spaces using Latin Hypercube Sampling method. It was developed for Latin Hypercube Sampling, model orchestration and simulation execution for a user-defined number of samples.

## Purpose

The script was developed to automate the generation and execution of retrofit samples for a microclimate-aware precinct-scale assessment. It links simulation inputs and outputs across the modelling workflow and records the results for subsequent analysis and prioritisation.

## Main script

- `custom_python_workflow.py`: Python script used for iterative Latin Hypercube Sampling, slider-driven model orchestration, result extraction, and CSV export.

## Software environment

The workflow was developed for Rhino 8 GhPython using CPython and Grasshopper-based modelling components. It was used together with established simulation tools including Dragonfly, Ladybug, Honeybee, and UWG.

## Outputs

The script exports:

- `design.csv`: Latin Hypercube Sampling design matrix
- `results.csv`: simulation outputs for each sample
- `run_meta.json`: metadata for reproducibility and run checking

## Reproducibility note

The repository provides the custom Python workflow used in the study. Some case-study input files, geometry, and simulation assets may not be publicly available due to project-specific or software-related constraints. Additional supporting data are available from the corresponding author upon reasonable request.

## Citation
The custom-developed Python workflow used in this study is archived on Zenodo as version v1.1.0:
https://doi.org/10.5281/zenodo.21236489
Please cite the archived repository release and the associated manuscript when using this code.

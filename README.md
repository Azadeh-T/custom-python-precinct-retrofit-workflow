# Custom Python Precinct Retrofit Workflow

This repository contains the custom-developed Python workflow used for the manuscript:

“A co-assessment framework for balancing outdoor thermal stress and operational carbon emissions in precinct-scale retrofit under urban microclimate conditions”

The workflow supports iterative precinct-scale retrofit assessment by orchestrating Latin Hypercube Sampling, model execution, and post-processing of operational CO₂e and PET-based outdoor thermal-stress indicators.

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

Please cite the associated manuscript and the archived repository release when using this code.

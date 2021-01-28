ECON-T software
===============

This repository contains some simple python software to work with the ECON-T
emulator running on a Zynq. It currently includes:

 - `align_links.py`: a script that does some initial setup of the ECON-T
   emulator system, including aligning the links in both the ECON-T and the
   link capture block

Setup instructions
------------------

You will need a PEP517 build tool.  This can be installed with `pip`:

```pip3 install pep517```

Then, in the top level directory of this repository, run:

```python3 -m pep517.build .```



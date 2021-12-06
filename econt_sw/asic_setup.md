# ECON-T P1 Testing

## Start-up:

- Start a server
```
# for ASIC
python3 zmq_server.py --addr 0x20 --server 5554
# for emulator
python3 zmq_server.py --addr 0x21 --server 5555
```

- To check all registers in ASIC:
```
source check_all.sh 
```

- To lock pll manually in ASIC:
```
source pll_manual.sh
```
This sets: `ref_clk_sel, fromMemToLJCDR_enableCapBankOverride, fromMemToLJCDR_CBOvcoCapSelect`.
And should change `pll_read_bytes_2to0_lfLocked 0x1`.
Then it should be in PUSM_state (8): `STATE_WAIT_CHNS_LOCK`

- Then, configure IO and send bit transitions:
```
python testing/uhal-align_on_tester.py --step bit-tr
```
This should change ` misc_ro_0_PUSM_state 0x9` (`STATE_FUNCTIONAL`).

- Then, set run bit in ASIC:
```
python3 testing/i2c_single_register.py --name MISC_run --value 1
```

## Alignment:

- First, set up the alignment registers 
```
# for ASIC
source align_set.sh  
# for emulator
```

- Then, send link reset ROC-T.
This also sends zeroes with headers and sets up the delay for emulator.
```
python testing/uhal-align_on_tester.py --step lr-roct
```

- Then, 
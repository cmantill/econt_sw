from time import sleep

GPIBAddresses={46:6,
              48:8,
              99:5,
              15:15,
              }

from PowerSupplyControls import Agilent3648A


if __name__=='__main__':

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--On', '--on', default=False, action='store_true', help='Turn on ECON-T ASIC')
    parser.add_argument('--Off', '--off', default=False, action='store_true', help='Turn off ECON-T ASIC')
    parser.add_argument('--disconnect', default=False, action='store_true', help='Disconnect gpib (set back to local mode')
    parser.add_argument('--read', default=False, action='store_true', help='Read power')
    parser.add_argument('--id', default=False, action='store_true', help='Get ID')
    parser.add_argument('--logging', default=False, action='store_true', help='Start power monitoring')
    parser.add_argument('--setVoltage', default=None, type=float, help='Voltage setting (1.2 V if left unset)')
    parser.add_argument('--logName', default='logFile.log', help='log name')
    parser.add_argument('--time', default=15, type=float,help='Frequency (in seconds) of how often to read the power')
    parser.add_argument('--ip', default='192.168.1.50', help='IP Address of the gpib controller')
    parser.add_argument('--addr', default=8, help='GPIB address of the power supply')
    parser.add_argument('--board', default=46, type=int, help='Board number of hexacontroller (used to determing which power supply to control)')

    args = parser.parse_args()

    ps=Agilent3648A(host=args.ip,addr=args.addr)

    if args.On:
        ps.SetLimits_2(v=0,i=0.6)
        if args.setVoltage is None:
            ps.SetLimits_1(v=1.2,i=0.6)
            ps.TurnOn()
        elif args.setVoltage>1.35:
            print(f'Voltage too high for ECON')
            print(f'V={args.setVoltage}')
            exit()
        else:
            ps.SetLimits_1(v=args.setVoltage,i=0.6)
            ps.TurnOn()
    elif args.Off:
        ps.TurnOff()
    elif args.setVoltage is not None:
        if args.setVoltage>1.35:
            print(f'Voltage too high for ECON')
            print(f'V={args.setVoltage}')
            exit()
        else:
            ps.SetLimits_1(v=args.setVoltage,i=0.6)            
    if args.id:
        print(ps.ID())
    if args.read:
        p,v,i=ps.ReadPower_1()
        print(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')
    if args.logging:
        import logging
        import time
        logging.basicConfig(filename=args.logName,
                            level=logging.INFO,
                            format='%(asctime)4s %(message)s',
                            )
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)4s %(message)s')
        console.setFormatter(formatter)
        logging.getLogger().addHandler(console)

        try:
            while True:
                p,v_ASIC,i_ASIC=ps.ReadPower_1()
                logging.info(f'Power: {"On" if int(p) else "Off"}, ASIC Voltage: {float(v_ASIC):.4f}, ASIC Current:{float(i_ASIC):.4f}')
                sleep(args.time)
        except KeyboardInterrupt:
            logging.info(f'Closing')

    if args.disconnect:
        ps.disconnect()



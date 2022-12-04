from plx_gpib_ethernet import PrologixGPIBEthernet
from time import sleep

GPIBAddresses={46:6,
              48:8,
              99:5,
              15:15,
              }

class psControl:
    def __init__(self, *args, **kwargs):
        self.gpib = PrologixGPIBEthernet(*args, **kwargs)
        self.board=None

    def close(self):
        self.gpib.close()

    def reconnect(self):
        self.gpib.reconnect()

    def disconnect(self):
        self.gpib.disconnect()

    def select(self,board):
        if not board is None:
            if board>30:
                addr=GPIBAddresses[board]
            else:
                addr=board
            self.gpib.select(addr)

    def ID(self,board):
        self.select(board)
        return self.gpib.query("*IDN?")[:-1]

    def SetVoltage(self, voltage):
        self.select(8)

        if float(voltage)<=1.5 and float(voltage) >= 0.9:
            self.gpib.write(f"V {voltage}")
            return True
        else:
            print(f'Selected voltage ({voltage}) outside of defined safe range 0.9-1.5')
            return False

    def ASICOn(self,voltage=None):
        self.select(8)
        x=self.gpib.query('++addr')

        if voltage is None:
            is_set=self.SetVoltage(None,1.2)
        else:
            is_set=self.SetVoltage(None,float(voltage))

        if is_set:
            self.gpib.write("I 0.6")
            self.gpib.write("OP 1")

    def ASICOff(self):
        self.select(8)
        x=self.gpib.query('++addr')
        self.gpib.write("OP 0")

    def Read_Power(self):
        self.select(8)
#        x=self.gpib.query('++addr')
#        print(x)
#        output=self.gpib.query("OUTP?")[:-1]
        output="1"
        v=self.gpib.query("VO?")[:-2]
        i=self.readCurrent()
#        i=self.gpib.query("IO?")[:-2]
        return output,v,i

    def ConfigRTD(self):
        self.select(12)
        self.gpib.write('*RST')
        self.gpib.write("FUNC 'FRES'")
        self.gpib.write("FRES:RANG 1E3")

    def readRTD(self):
        self.select(12)
        resistance=float(self.gpib.query(":READ?"))
#        resistance=float(self.gpib.read()[:-1])
        temperature=((resistance/1000)-1)/0.00385
        return temperature, resistance
        
    def ConfigReadCurrent(self):
        self.select(12)
        self.gpib.write("*RST")
        self.gpib.write("FUNC 'CURR:DC'")
        self.gpib.write("CURR:RANGE 1.")

    def readCurrent(self):
        self.select(12)
        current=float(self.gpib.query(":READ?"))
        return current

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--On', '--on', default=False, action='store_true', help='Turn on ECON-T ASIC')
    parser.add_argument('--Off', '--off', default=False, action='store_true', help='Turn off ECON-T ASIC')
    parser.add_argument('--disconnect', default=False, action='store_true', help='Disconnect gpib (set back to local mode')
    parser.add_argument('--read', default=False, action='store_true', help='Read power')
    parser.add_argument('--id', default=False, action='store_true', help='Get ID')
    parser.add_argument('--logging', default=False, action='store_true', help='Start power monitoring')
    parser.add_argument('--setVoltage', default=None, help='Voltage setting (1.2 V if left unset)')
    parser.add_argument('--logName', default='logFile.log', help='log name')
    parser.add_argument('--time', default=15, type=float,help='Frequency (in seconds) of how often to read the power')
    parser.add_argument('--ip', default='192.168.206.50', help='IP Address of the gpib controller')
    parser.add_argument('--board', default=46, type=int, help='Board number of hexacontroller (used to determing which power supply to control)')

    args = parser.parse_args()

    ps=psControl(host=args.ip)


    if args.On:
        ps.ASICOn(args.board,args.setVoltage)
    if args.Off:
        ps.ASICOff(args.board)
    if not args.On and not args.setVoltage is None:
        ps.SetVoltage(args.board,args.setVoltage)
    if args.id:
        print(ps.ID(args.board))
    if args.read:
        p,v,i=ps.Read_Power()
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
                on_ASIC,v_ASIC,i_ASIC=ps.Read_Power()
                logging.info(f'Power: {"On" if int(p) else "Off"}, ASIC Voltage: {float(v_ASIC):.4f}, ASIC Current:{float(i_ASIC):.4f}')
                sleep(args.time)
        except KeyboardInterrupt:
            logging.info(f'Closing')

    if args.disconnect:
        ps.select(args.board)
        ps.disconnect()
        
    ps.close()

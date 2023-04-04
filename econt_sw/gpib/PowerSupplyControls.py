from plx_gpib_ethernet import PrologixGPIBEthernet

class gpibControl:
    def __init__(self, host, addr):
        self.gpib = PrologixGPIBEthernet(host=host)
        self.gpib.connect()
        self.addr=addr

    def close(self):
        self.gpib.close()

    def connect(self):
        self.gpib.connect()

    def reconnect(self):
        self.gpib.reconnect()

    def disconnect(self):
        self.gpib.disconnect()

    def select(self):
        if not self.addr is None:
            self.gpib.select(self.addr)
            # if self.addr>30:
            #     addr=GPIBAddresses[self.addr]
            # else:
            #     addr=board
            # self.gpib.select(addr)

    def ID(self):
        self.select()
        return self.gpib.query("*IDN?")[:-1]

    def testQuery(self,q):
        self.select()
        return self.gpib.query(q)[:-1]


class Agilent3648A(gpibControl):
    def IsOn(self):
        self.select()
        return self.gpib.query("OUTP:STAT?")[:-1]

    def TurnOn(self):
        self.gpib.write("OUTP ON")

    def TurnOff(self):
        self.gpib.write("OUTP OFF")

    def ReadPower(self, output):
        self.select()
        v=self.gpib.query(f"INST:SEL OUT{output}\nMEAS:VOLT?")[:-1]
        i=self.gpib.query(f"INST:SEL OUT{output}\nMEAS:CURR?")[:-1]
        p=self.gpib.query("OUTP:STAT?")[:-1]
        return int(p), float(v),float(i)

    def ReadPower_1(self):
        return self.ReadPower(1)

    def ReadPower_2(self):
        return self.ReadPower(2)

    def ReadLimits(self, output):
        self.select()
        v=self.gpib.query(f"INST:SEL OUT{output}\nVOLT?")[:-1]
        i=self.gpib.query(f"INST:SEL OUT{output}\nCURR?")[:-1]
        return float(v),float(i)

    def ReadLimits_1(self):
        return self.ReadLimits(1)

    def ReadLimits_2(self):
        return self.ReadLimits(2)

    def SetLimits(self, output, voltage, current):
        self.gpib.write(f"INST:SEL OUT{output}\nVOLT {voltage}")
        self.gpib.write(f"INST:SEL OUT{output}\nCURR {current}")

    def SetLimits_1(self,v=1.2,i=0.6):
        self.SetLimits(output=1, voltage=v, current=i)

    def SetLimits_2(self,v=1.2,i=0.6):
        self.SetLimits(output=2, voltage=v, current=i)



class ObelixSupplies(gpibControl):
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

#ifndef ELINKOUTPUTSBLOCKHANDLER
#define ELINKOUTPUTSBLOCKHANDLER 1

#include <uhal/uhal.hpp>
#include <yaml-cpp/yaml.h>

class eLinkOutputsBlockHandler
{
 public:
  eLinkOutputsBlockHandler(){;}
  eLinkOutputsBlockHandler(uhal::HwInterface* uhalHW,
			   std::string eLink_outputs_switch_name,
			   std::string eLink_outputs_stream_name);
  ~eLinkOutputsBlockHandler(){;}

  void setSwitchRegister(std::string elink, std::string regName, uint32_t value);
  void setStreamRegister(std::string elink, std::string regName, uint32_t value);

 private:
  uhal::HwInterface* m_uhalHW;
  std::string m_switch_block_name; //same names as in the address_table/fw_block_addresses.xml file 
  std::string m_stream_block_name;
};

#endif
